import argparse
from html import unescape
from html.parser import HTMLParser

import psycopg
import torch
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer


_BLOCK_TAGS = {
    "br",
    "div",
    "p",
    "pre",
    "blockquote",
    "li",
    "ul",
    "ol",
    "table",
    "tr",
    "td",
    "th",
    "hr",
}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag) -> None:
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data) -> None:
        if data:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def clean_html_text(text: str | None) -> str:
    if not text:
        return ""
    parser = _HTMLTextExtractor()
    parser.feed(text)
    parser.close()
    cleaned = unescape(parser.get_text())
    return " ".join(cleaned.split())


def build_text(title, body):
    title = clean_html_text(title)
    body = clean_html_text(body)
    return (title + "\n\n" + body).strip()


def main():
    parser = argparse.ArgumentParser(description="Embed posts with a local model.")
    parser.add_argument("--dsn", required=True, help="Postgres DSN")
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Torch device override (e.g. cuda, cuda:0, cpu). Defaults to cuda if available.",
    )
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--min-text-len", type=int, default=10)
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Clear existing embeddings before rebuilding.",
    )
    args = parser.parse_args()

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"loading model on device: {device}")
    model = SentenceTransformer(args.model, device=device)
    dim = model.get_sentence_embedding_dimension()
    zero_vector = [0.0] * dim

    with psycopg.connect(args.dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            if args.rebuild:
                cur.execute("UPDATE posts SET embedding = NULL WHERE embedding IS NOT NULL")
                conn.commit()
                print("cleared embeddings: rebuilding from scratch")

            total = 0
            while True:
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

                if texts:
                    embeddings = model.encode(texts, normalize_embeddings=True)
                    update_rows = [(embeddings[i], ids[i]) for i in range(len(ids))]
                else:
                    update_rows = []

                if skip_ids:
                    cur.executemany(
                        "UPDATE posts SET embedding = %s WHERE id = %s",
                        [(zero_vector, i) for i in skip_ids],
                    )
                if update_rows:
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
