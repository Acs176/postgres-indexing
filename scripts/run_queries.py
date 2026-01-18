#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

import psycopg


@dataclass
class QueryResult:
    query_index: int
    query: str
    plan_file: str
    planning_time_ms: Optional[float]
    execution_time_ms: Optional[float]
    client_time_ms: float
    top_actual_rows: Optional[float]


def _split_sql_statements(text: str) -> List[str]:
    statements: List[str] = []
    buf: List[str] = []

    i = 0
    n = len(text)
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    in_dollar: Optional[str] = None
    dollar_re = re.compile(r"\$[A-Za-z0-9_]*\$")

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                i += 2
                in_block_comment = False
            else:
                i += 1
            continue

        if in_dollar is not None:
            if text.startswith(in_dollar, i):
                buf.append(in_dollar)
                i += len(in_dollar)
                in_dollar = None
            else:
                buf.append(ch)
                i += 1
            continue

        if not in_single and not in_double:
            if ch == "-" and nxt == "-":
                if buf and not buf[-1].isspace():
                    buf.append(" ")
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                if buf and not buf[-1].isspace():
                    buf.append(" ")
                in_block_comment = True
                i += 2
                continue
            if ch == "$":
                match = dollar_re.match(text[i:])
                if match:
                    in_dollar = match.group(0)
                    buf.append(in_dollar)
                    i += len(in_dollar)
                    continue

        if in_single:
            if ch == "'" and nxt == "'":
                buf.append(ch)
                buf.append(nxt)
                i += 2
                continue
            if ch == "'":
                in_single = False
            buf.append(ch)
            i += 1
            continue

        if in_double:
            if ch == '"' and nxt == '"':
                buf.append(ch)
                buf.append(nxt)
                i += 2
                continue
            if ch == '"':
                in_double = False
            buf.append(ch)
            i += 1
            continue

        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue

        if ch == '"':
            in_double = True
            buf.append(ch)
            i += 1
            continue

        if ch == ";":
            statement = "".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_json(path: str, payload: object) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _run_explain(
    cursor: psycopg.Cursor,
    query: str,
) -> dict:
    cursor.execute(
        "EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON) " + query
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("EXPLAIN returned no rows")
    return row[0][0]


def _summarize_plan(plan: dict) -> tuple[Optional[float], Optional[float], Optional[float]]:
    planning_time = plan.get("Planning Time")
    execution_time = plan.get("Execution Time")
    top_rows = None
    top_plan = plan.get("Plan")
    if isinstance(top_plan, dict):
        top_rows = top_plan.get("Actual Rows")
    return planning_time, execution_time, top_rows


def _add_if_present(payload: dict, node: dict, key: str, out_key: str) -> None:
    value = node.get(key)
    if value is not None:
        payload[out_key] = value


def _extract_plan_nodes(node: dict, depth: int, out: List[dict]) -> None:
    item: dict = {"node_type": node.get("Node Type"), "depth": depth}
    _add_if_present(item, node, "Relation Name", "relation")
    _add_if_present(item, node, "Index Name", "index")
    _add_if_present(item, node, "Actual Rows", "actual_rows")
    _add_if_present(item, node, "Actual Loops", "actual_loops")
    _add_if_present(item, node, "Actual Total Time", "actual_total_time_ms")
    _add_if_present(item, node, "Plan Rows", "plan_rows")
    _add_if_present(item, node, "Plan Width", "plan_width")
    _add_if_present(item, node, "Total Cost", "plan_total_cost")
    _add_if_present(item, node, "Filter", "filter")
    _add_if_present(item, node, "Index Cond", "index_cond")
    _add_if_present(item, node, "Recheck Cond", "recheck_cond")
    _add_if_present(item, node, "Hash Cond", "hash_cond")
    _add_if_present(item, node, "Merge Cond", "merge_cond")
    _add_if_present(item, node, "Join Filter", "join_filter")
    _add_if_present(item, node, "Sort Key", "sort_key")
    _add_if_present(item, node, "Group Key", "group_key")
    _add_if_present(item, node, "Shared Hit Blocks", "shared_hit_blocks")
    _add_if_present(item, node, "Shared Read Blocks", "shared_read_blocks")
    _add_if_present(item, node, "Shared Dirtied Blocks", "shared_dirtied_blocks")
    _add_if_present(item, node, "Shared Written Blocks", "shared_written_blocks")
    _add_if_present(item, node, "Temp Read Blocks", "temp_read_blocks")
    _add_if_present(item, node, "Temp Written Blocks", "temp_written_blocks")
    out.append(item)

    for child in node.get("Plans", []) or []:
        if isinstance(child, dict):
            _extract_plan_nodes(child, depth + 1, out)


def _distill_plan(plan: dict) -> dict:
    planning_time, execution_time, top_rows = _summarize_plan(plan)
    nodes: List[dict] = []
    top_plan = plan.get("Plan")
    if isinstance(top_plan, dict):
        _extract_plan_nodes(top_plan, 0, nodes)
    return {
        "planning_time_ms": planning_time,
        "execution_time_ms": execution_time,
        "top_actual_rows": top_rows,
        "plan_nodes": nodes,
    }


def _iter_queries(path: str) -> Iterable[str]:
    with open(path, "r", encoding="utf-8") as handle:
        contents = handle.read()
    for statement in _split_sql_statements(contents):
        if statement.strip():
            yield statement


def _run_queries(
    dsn: str,
    sql_file: str,
    out_dir: str,
    statement_timeout_ms: Optional[int],
) -> List[QueryResult]:
    results: List[QueryResult] = []
    _ensure_dir(out_dir)

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            if statement_timeout_ms is not None:
                cur.execute("SET statement_timeout TO %s", (statement_timeout_ms,))

            for idx, query in enumerate(_iter_queries(sql_file), start=1):
                start = time.perf_counter()
                raw_plan = _run_explain(cur, query)
                elapsed_ms = (time.perf_counter() - start) * 1000.0

                plan_filename = f"query_{idx:03d}_plan.json"
                plan_path = os.path.join(out_dir, plan_filename)
                distilled_plan = _distill_plan(raw_plan)
                _write_json(plan_path, distilled_plan)

                planning_time = distilled_plan.get("planning_time_ms")
                execution_time = distilled_plan.get("execution_time_ms")
                top_rows = distilled_plan.get("top_actual_rows")
                results.append(
                    QueryResult(
                        query_index=idx,
                        query=query,
                        plan_file=plan_filename,
                        planning_time_ms=planning_time,
                        execution_time_ms=execution_time,
                        client_time_ms=elapsed_ms,
                        top_actual_rows=top_rows,
                    )
                )
    return results


def _write_summary(out_dir: str, run_id: str, results: List[QueryResult]) -> str:
    summary_path = os.path.join(out_dir, f"{run_id}_summary.jsonl")
    with open(summary_path, "w", encoding="utf-8") as handle:
        for result in results:
            payload = {
                "query_index": result.query_index,
                "query": result.query,
                "plan_file": result.plan_file,
                "planning_time_ms": result.planning_time_ms,
                "execution_time_ms": result.execution_time_ms,
                "client_time_ms": result.client_time_ms,
                "top_actual_rows": result.top_actual_rows,
            }
            handle.write(json.dumps(payload) + "\n")
    return summary_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SQL queries with EXPLAIN ANALYZE and store timings + plans."
    )
    parser.add_argument("--dsn", required=True, help="Postgres DSN")
    parser.add_argument("--sql-file", required=True, help="Path to .sql file")
    parser.add_argument(
        "--out-dir",
        default=os.path.join("monitoring", "query_runs"),
        help="Directory for plans and summaries",
    )
    parser.add_argument(
        "--statement-timeout-ms",
        type=int,
        default=None,
        help="Optional statement_timeout in milliseconds",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run identifier for summary file naming",
    )

    args = parser.parse_args()

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join(args.out_dir, run_id)
    _ensure_dir(out_dir)

    results = _run_queries(
        dsn=args.dsn,
        sql_file=args.sql_file,
        out_dir=out_dir,
        statement_timeout_ms=args.statement_timeout_ms,
    )
    summary_path = _write_summary(out_dir, run_id, results)

    print(f"Wrote {len(results)} query plans to {out_dir}")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
