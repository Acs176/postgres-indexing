#!/usr/bin/env python3
from __future__ import annotations

import argparse

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Embed a text query and run a vector search against posts."
    )
    parser.add_argument("--dsn", required=True, help="Postgres DSN")
    parser.add_argument("--query", required=True, help="Query text to embed")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model",
    )
    args = parser.parse_args()

    model = SentenceTransformer(args.model)
    embedding = model.encode([args.query], normalize_embeddings=True)[0]

    with psycopg.connect(args.dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, body
                FROM posts
                WHERE embedding <#> embedding <> 0
                AND post_type_id = 1
                ORDER BY embedding <-> %s
                LIMIT %s
                """,
                (embedding, args.limit),
            )
            rows = cur.fetchall()

    for row in rows:
        print(f"{row[0]}\t{row[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
