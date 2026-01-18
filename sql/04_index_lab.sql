-- Index Lab Queries
-- Use with: EXPLAIN ANALYZE <query>;

-- Query 1: range filter + sort (B-tree on creation_date)
SELECT id, title, creation_date
FROM posts
WHERE creation_date >= now() - interval '365 days'
ORDER BY creation_date DESC
LIMIT 50;

-- Query 2: equality filter (B-tree on owner_user_id)
SELECT id, title, owner_user_id
FROM posts
WHERE owner_user_id = 12345
LIMIT 50;

-- Query 3: array contains (GIN on tags)
SELECT id, title, tags
FROM posts
WHERE tags @> ARRAY['postgresql']
LIMIT 50;

-- Query 4: full-text search (GIN on search_tsv)
SELECT id, title
FROM posts
WHERE search_tsv @@ plainto_tsquery('english', 'btree gin index')
ORDER BY ts_rank(search_tsv, plainto_tsquery('english', 'btree gin index')) DESC
LIMIT 50;

-- Query 5: vector similarity (ivfflat on embedding)
SELECT id, title
FROM posts
WHERE embedding IS NOT NULL
ORDER BY embedding <-> :'qvec'::vector
LIMIT 50;
