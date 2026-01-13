# DB Indexing Playground (Postgres + pgvector + Stack Exchange dump)

This repo is a small, script-driven playground to learn:
- classic Postgres indexes (btree, GIN, full-text search)
- vector indexing with pgvector
- how indexes change query performance

Data source: Stack Exchange public data dump (XML).

## Prereqs
- Postgres 14+ (or similar)
- pgvector extension installed in Postgres
- Python 3.10+

## Setup
1) Create a database and enable pgvector:
```sql
CREATE DATABASE se_indexing;
\\c se_indexing
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
psql "postgresql://USER:PASSWORD@localhost:5432/se_indexing" -f sql/01_schema.sql
```
Note: the `embedding` column is `vector(384)` to match the default model.

## Load data (posts + users + comments)
Example load from the Meta Stack Exchange dump:
```powershell
python scripts/01_load_xml.py `
  --dsn "postgresql://USER:PASSWORD@localhost:5432/se_indexing" `
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
psql "postgresql://USER:PASSWORD@localhost:5432/se_indexing" -f sql/02_indexes.sql
```

For ivfflat, run:
```sql
ANALYZE posts;
```

## Add embeddings
This uses a local model (no API):
```powershell
python scripts/02_embed_posts.py `
  --dsn "postgresql://USER:PASSWORD@localhost:5432/se_indexing" `
  --batch-size 200 `
  --max-rows 50000
```

## Try example queries
```powershell
psql "postgresql://USER:PASSWORD@localhost:5432/se_indexing" -f sql/03_queries.sql
```