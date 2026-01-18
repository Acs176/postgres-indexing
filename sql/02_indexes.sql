-- Run after loading data for faster ingestion.

CREATE INDEX IF NOT EXISTS posts_creation_date_idx ON posts (creation_date);
CREATE INDEX IF NOT EXISTS posts_owner_user_id_idx ON posts (owner_user_id);
-- CREATE INDEX IF NOT EXISTS posts_post_type_id_idx ON posts (post_type_id);

-- CREATE INDEX IF NOT EXISTS comments_post_id_idx ON comments (post_id);
-- CREATE INDEX IF NOT EXISTS comments_user_id_idx ON comments (user_id);

-- CREATE INDEX IF NOT EXISTS users_reputation_idx ON users (reputation);

CREATE INDEX IF NOT EXISTS posts_tags_gin ON posts USING GIN (tags);
CREATE INDEX IF NOT EXISTS posts_search_tsv_gin ON posts USING GIN (search_tsv);

-- Vector index (run after embeddings are populated).
CREATE INDEX IF NOT EXISTS posts_embedding_ivfflat
    ON posts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
