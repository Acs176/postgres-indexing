CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS posts (
    id integer PRIMARY KEY,
    post_type_id integer,
    parent_id integer,
    accepted_answer_id integer,
    creation_date timestamp,
    score integer,
    view_count integer,
    body text,
    owner_user_id integer,
    owner_display_name text,
    last_editor_user_id integer,
    last_editor_display_name text,
    last_edit_date timestamp,
    last_activity_date timestamp,
    title text,
    tags text[],
    answer_count integer,
    comment_count integer,
    favorite_count integer,
    closed_date timestamp,
    community_owned_date timestamp,
    content_license text,
    embedding vector(384),
    search_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))
    ) STORED
);

CREATE TABLE IF NOT EXISTS users (
    id integer PRIMARY KEY,
    reputation integer,
    creation_date timestamp,
    display_name text,
    last_access_date timestamp,
    website_url text,
    location text,
    about_me text,
    views integer,
    up_votes integer,
    down_votes integer,
    profile_image_url text,
    email_hash text,
    account_id integer
);

CREATE TABLE IF NOT EXISTS comments (
    id integer PRIMARY KEY,
    post_id integer,
    score integer,
    text text,
    creation_date timestamp,
    user_display_name text,
    user_id integer,
    content_license text
);
