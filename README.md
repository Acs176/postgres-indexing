# DB Indexing Playground (Postgres + pgvector + Stack Exchange dump)

This repo is a small, script-driven playground to learn:
- classic Postgres indexes (btree, GIN, full-text search)
- vector indexing with pgvector
- how indexes change query performance

Data source: Stack Exchange public data dump (XML).

## Prereqs
- Postgres 15+ (or similar)
- pgvector extension installed in Postgres
- Python 3.10+

## Setup
1) Create a database and enable pgvector:
```sql
\\c lab
CREATE EXTENSION IF NOT EXISTS vector;
```

2) Create a virtual env and install deps:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3) Create tables:
```powershell
psql "postgresql://postgres:postgres@pg-lab:5432/lab" -f sql/01_schema.sql
```
Note: the `embedding` column is `vector(384)` to match the default model.

## Load data (posts + users + comments)
Example load from the Meta Stack Exchange dump:
```powershell
python scripts/01_load_xml.py `
  --dsn "postgresql://postgres:postgres@pg-lab:5432/lab" `
  --posts "meta.stackexchange.com/Posts.xml" `
  --users "meta.stackexchange.com/Users.xml" `
  --comments "meta.stackexchange.com/Comments.xml" `
  --limit 100000
```

Notes:
- `--limit` keeps the dataset small while experimenting.
- Re-running the loader is safe (it uses `ON CONFLICT DO NOTHING`).

## Add indexes
Create indexes after loading data:
```powershell
psql "postgresql://postgres:postgres@pg-lab:5432/lab" -f sql/02_indexes.sql
```

For ivfflat, run:
```sql
ANALYZE posts;
```

## Add embeddings
This uses a local model (no API):
```powershell
python scripts/embed_posts.py `
  --dsn "postgresql://postgres:postgres@pg-lab:5432/lab" `
  --batch-size 200 `
  --max-rows 50000
```

## Try example queries
```powershell
psql "postgresql://postgres:postgres@pg-lab:5432/lab" -f sql/03_queries.sql
```

## Capture query plans + timings
Run the query runner to store EXPLAIN ANALYZE plans and timing data:
```powershell
python scripts/run_queries.py `
  --dsn "postgresql://postgres:postgres@pg-lab:5432/lab" `
  --sql-file sql/03_queries.sql
```
Outputs are written under `monitoring/query_runs/<run-id>/` with per-query plan JSON
files (distilled plan details) and a `*_summary.jsonl` file containing timings.
