import argparse
import xml.etree.ElementTree as ET

import psycopg


def parse_tags(raw):
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if raw[0] == "<" and raw[-1] == ">":
        raw = raw[1:-1]
    if not raw:
        return None
    return raw.split("><")


def get_int(attrs, key):
    value = attrs.get(key)
    return int(value) if value is not None else None


def get_text(attrs, key):
    return attrs.get(key)


def iter_rows(path, limit=None):
    count = 0
    context = ET.iterparse(path, events=("end",))
    for _, elem in context:
        if elem.tag != "row":
            continue
        yield elem.attrib
        elem.clear()
        count += 1
        if limit and count >= limit:
            break


def load_posts(conn, path, limit, batch_size):
    sql = """
        INSERT INTO posts (
            id, post_type_id, parent_id, accepted_answer_id, creation_date,
            score, view_count, body, owner_user_id, owner_display_name,
            last_editor_user_id, last_editor_display_name, last_edit_date,
            last_activity_date, title, tags, answer_count, comment_count,
            favorite_count, closed_date, community_owned_date, content_license
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (id) DO NOTHING
    """
    rows = []
    total = 0
    with conn.cursor() as cur:
        for attrs in iter_rows(path, limit=limit):
            rows.append(
                (
                    get_int(attrs, "Id"),
                    get_int(attrs, "PostTypeId"),
                    get_int(attrs, "ParentId"),
                    get_int(attrs, "AcceptedAnswerId"),
                    get_text(attrs, "CreationDate"),
                    get_int(attrs, "Score"),
                    get_int(attrs, "ViewCount"),
                    get_text(attrs, "Body"),
                    get_int(attrs, "OwnerUserId"),
                    get_text(attrs, "OwnerDisplayName"),
                    get_int(attrs, "LastEditorUserId"),
                    get_text(attrs, "LastEditorDisplayName"),
                    get_text(attrs, "LastEditDate"),
                    get_text(attrs, "LastActivityDate"),
                    get_text(attrs, "Title"),
                    parse_tags(get_text(attrs, "Tags")),
                    get_int(attrs, "AnswerCount"),
                    get_int(attrs, "CommentCount"),
                    get_int(attrs, "FavoriteCount"),
                    get_text(attrs, "ClosedDate"),
                    get_text(attrs, "CommunityOwnedDate"),
                    get_text(attrs, "ContentLicense"),
                )
            )
            if len(rows) >= batch_size:
                cur.executemany(sql, rows)
                conn.commit()
                total += len(rows)
                print(f"posts: {total}")
                rows = []
        if rows:
            cur.executemany(sql, rows)
            conn.commit()
            total += len(rows)
            print(f"posts: {total}")


def load_users(conn, path, limit, batch_size):
    sql = """
        INSERT INTO users (
            id, reputation, creation_date, display_name, last_access_date,
            website_url, location, about_me, views, up_votes, down_votes,
            profile_image_url, email_hash, account_id
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (id) DO NOTHING
    """
    rows = []
    total = 0
    with conn.cursor() as cur:
        for attrs in iter_rows(path, limit=limit):
            rows.append(
                (
                    get_int(attrs, "Id"),
                    get_int(attrs, "Reputation"),
                    get_text(attrs, "CreationDate"),
                    get_text(attrs, "DisplayName"),
                    get_text(attrs, "LastAccessDate"),
                    get_text(attrs, "WebsiteUrl"),
                    get_text(attrs, "Location"),
                    get_text(attrs, "AboutMe"),
                    get_int(attrs, "Views"),
                    get_int(attrs, "UpVotes"),
                    get_int(attrs, "DownVotes"),
                    get_text(attrs, "ProfileImageUrl"),
                    get_text(attrs, "EmailHash"),
                    get_int(attrs, "AccountId"),
                )
            )
            if len(rows) >= batch_size:
                cur.executemany(sql, rows)
                conn.commit()
                total += len(rows)
                print(f"users: {total}")
                rows = []
        if rows:
            cur.executemany(sql, rows)
            conn.commit()
            total += len(rows)
            print(f"users: {total}")


def load_comments(conn, path, limit, batch_size):
    sql = """
        INSERT INTO comments (
            id, post_id, score, text, creation_date, user_display_name, user_id,
            content_license
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """
    rows = []
    total = 0
    with conn.cursor() as cur:
        for attrs in iter_rows(path, limit=limit):
            rows.append(
                (
                    get_int(attrs, "Id"),
                    get_int(attrs, "PostId"),
                    get_int(attrs, "Score"),
                    get_text(attrs, "Text"),
                    get_text(attrs, "CreationDate"),
                    get_text(attrs, "UserDisplayName"),
                    get_int(attrs, "UserId"),
                    get_text(attrs, "ContentLicense"),
                )
            )
            if len(rows) >= batch_size:
                cur.executemany(sql, rows)
                conn.commit()
                total += len(rows)
                print(f"comments: {total}")
                rows = []
        if rows:
            cur.executemany(sql, rows)
            conn.commit()
            total += len(rows)
            print(f"comments: {total}")


def main():
    parser = argparse.ArgumentParser(description="Load Stack Exchange XML data.")
    parser.add_argument("--dsn", required=True, help="Postgres DSN")
    parser.add_argument("--posts", help="Path to Posts.xml")
    parser.add_argument("--users", help="Path to Users.xml")
    parser.add_argument("--comments", help="Path to Comments.xml")
    parser.add_argument("--limit", type=int, default=None, help="Max rows per file")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--connect-timeout", type=int, default=10)
    args = parser.parse_args()

    print("Connecting to DB...")
    with psycopg.connect(args.dsn, connect_timeout=args.connect_timeout) as conn:
        print("Connected to DB!")
        if args.posts:
            load_posts(conn, args.posts, args.limit, args.batch_size)
        if args.users:
            load_users(conn, args.users, args.limit, args.batch_size)
        if args.comments:
            load_comments(conn, args.comments, args.limit, args.batch_size)


if __name__ == "__main__":
    main()
