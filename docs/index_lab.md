# Index Lab

Goal: build intuition for why each index exists by comparing query plans and timings.

## Setup
1) Load data (at least 50k posts).
2) Create indexes:
   psql "postgresql://USER:PASSWORD@localhost:5432/se_indexing" -f sql/02_indexes.sql
3) Run ANALYZE:
   psql "postgresql://USER:PASSWORD@localhost:5432/se_indexing" -c "ANALYZE;"

## How to run the lab
- Use EXPLAIN ANALYZE to see both plan shape and timing.
- Run each query twice: once with the index, once without.
- To test "without index", drop it, re-run ANALYZE, then re-create it.

## Index map (what the index is for)
- B-tree: equality, range, and order-by on scalar columns.
- GIN: membership or token search inside arrays/tsvector.
- ivfflat: approximate nearest neighbor on embeddings.

## Steps
A) B-tree on posts.creation_date
1) Run query 1 (range filter + sort).
2) Observe seq scan vs index scan.

B) B-tree on posts.owner_user_id
1) Run query 2 (equality filter).
2) Observe index scan + fewer rows visited.

C) GIN on posts.tags
1) Run query 3 (array contains).
2) Observe bitmap index scan on GIN.

D) GIN on posts.search_tsv
1) Run query 4 (full-text search).
2) Observe bitmap index scan on tsvector.

E) ivfflat on posts.embedding
1) Run query 5 (vector similarity).
2) Compare probes = 1 vs 10 vs 50.

## Notes
- If the planner still chooses a seq scan with the index present, it can be due to low selectivity, small table size, or outdated stats. Try ANALYZE and verify row counts.
- You can temporarily force index usage for learning by disabling seq scans:
  SET enable_seqscan = off;
