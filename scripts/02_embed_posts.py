import argparse

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer


def build_text(title, body):
    title = title or ""
    body = body or ""
    return (title + "\n\n" + body).strip()


def main():
    parser = argparse.ArgumentParser(description="Embed posts with a local model.")
    parser.add_argument("--dsn", required=True, help="Postgres DSN")
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model",
    )
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--min-text-len", type=int, default=10)
    args = parser.parse_args()

    model = SentenceTransformer(args.model)
    dim = model.get_sentence_embedding_dimension()
    zero_vector = [0.0] * dim

    with psycopg.connect(args.dsn) as conn:
        register_vector(conn)
        total = 0
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, body
                    FROM posts
                    WHERE embedding IS NULL
                    ORDER BY id
                    LIMIT %s
                    """,
                    (args.batch_size,),
                )
                rows = cur.fetchall()
            if not rows:
                break

            texts = []
            ids = []
            skip_ids = []
            for row in rows:
                text = build_text(row[1], row[2]) ## title, body
                if len(text) < args.min_text_len:
                    skip_ids.append(row[0]) ## id
                    continue
                texts.append(text)
                ids.append(row[0]) ## id

            with conn.cursor() as cur:
                if skip_ids:
                    cur.executemany(
                        "UPDATE posts SET embedding = %s WHERE id = %s",
                        [(zero_vector, i) for i in skip_ids],
                    )

                if texts:
                    embeddings = model.encode(texts, normalize_embeddings=True)
                    update_rows = [(embeddings[i], ids[i]) for i in range(len(ids))]
                    cur.executemany(
                        "UPDATE posts SET embedding = %s WHERE id = %s",
                        update_rows,
                    )

                conn.commit()

            total += len(texts) + len(skip_ids)
            print(f"embedded: {total}")

            if args.max_rows and total >= args.max_rows:
                break


if __name__ == "__main__":
    main()
