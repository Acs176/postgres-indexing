-- Example: find recent high-score questions
SELECT id, title, score, creation_date
FROM posts
WHERE post_type_id = 1
ORDER BY score DESC
LIMIT 10;

-- Example: tag filter using GIN index
SELECT id, title, tags
FROM posts
WHERE tags @> ARRAY['postgresql']
LIMIT 10;

-- Example: full-text search
SELECT id, title
FROM posts
WHERE search_tsv @@ plainto_tsquery('english', 'index btree vs gin')
ORDER BY ts_rank(search_tsv, plainto_tsquery('english', 'index btree vs gin')) DESC
LIMIT 10;

-- Example: vector similarity (replace with a real vector)
-- SET ivfflat.probes = 10;
-- SELECT id, title
-- FROM posts
-- ORDER BY embedding <-> '[0.1, 0.2, ...]'::vector
-- LIMIT 5;
