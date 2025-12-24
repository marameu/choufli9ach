import json
import mimetypes
import os
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote
import base64


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "orders.db"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")


def is_authorized(handler: BaseHTTPRequestHandler) -> bool:
    auth_header = handler.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    username, _, password = decoded.partition(":")
    return username == "admin" and password == ADMIN_PASSWORD


def render_admin_page(orders: list[dict]) -> bytes:
    rows = []
    for order in orders:
        items = ", ".join(
            f"{item.get('name', '')} ({item.get('size', '')})"
            for item in order.get("items", [])
        )
        rows.append(
            f"""
            <tr>
              <td>{order["id"]}</td>
              <td>{order["name"]}</td>
              <td>{order["phone"]}</td>
              <td>{order["address"]}</td>
              <td>{items}</td>
              <td>{order["total"]} TND</td>
              <td>{order["created_at"]}</td>
            </tr>
            """
        )

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Admin - Commandes</title>
      <style>
        body {{
          font-family: "Fira Sans", Arial, sans-serif;
          background: #f7f1e7;
          color: #1b1916;
          margin: 0;
          padding: 40px 24px;
        }}
        h1 {{
          margin-bottom: 20px;
          font-size: 1.8rem;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          background: #fff;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 20px 40px rgba(10, 8, 6, 0.12);
        }}
        th, td {{
          padding: 12px 14px;
          text-align: left;
          border-bottom: 1px solid #efe6d7;
          font-size: 0.9rem;
        }}
        th {{
          background: #1b1916;
          color: #fff;
          text-transform: uppercase;
          letter-spacing: 0.06rem;
          font-size: 0.75rem;
        }}
        tr:last-child td {{
          border-bottom: none;
        }}
      </style>
    </head>
    <body>
      <h1>Commandes recentes</h1>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nom</th>
            <th>Telephone</th>
            <th>Adresse</th>
            <th>Articles</th>
            <th>Total</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows) if rows else '<tr><td colspan="7">Aucune commande.</td></tr>'}
        </tbody>
      </table>
    </body>
    </html>
    """
    return html.encode("utf-8")


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                items_json TEXT NOT NULL,
                total INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def read_static_file(path: Path) -> tuple[bytes, str]:
    content = path.read_bytes()
    mime_type, _ = mimetypes.guess_type(path.name)
    return content, (mime_type or "application/octet-stream")


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "ChoufliAPI/0.1"

    def _set_headers(self, status: int, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_OPTIONS(self) -> None:
        self._set_headers(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        if self.path.startswith("/api/orders"):
            self.handle_list_orders()
            return

        if self.path.startswith("/admin"):
            if not is_authorized(self):
                self.send_response(HTTPStatus.UNAUTHORIZED)
                self.send_header("WWW-Authenticate", 'Basic realm="Admin"')
                self.end_headers()
                return
            self.handle_admin_page()
            return

        path = unquote(self.path.split("?", 1)[0])
        if path == "/":
            path = "/index.html"
        file_path = (BASE_DIR / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(BASE_DIR)) or not file_path.exists():
            self._set_headers(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8")
            self.wfile.write(b"Not found")
            return

        try:
            content, mime_type = read_static_file(file_path)
        except OSError:
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR, "text/plain; charset=utf-8")
            self.wfile.write(b"Failed to read file")
            return

        self._set_headers(HTTPStatus.OK, mime_type)
        self.wfile.write(content)

    def do_POST(self) -> None:
        if self.path.startswith("/api/orders"):
            self.handle_create_order()
            return

        self._set_headers(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8")
        self.wfile.write(b"Not found")

    def handle_create_order(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b""
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode("utf-8"))
            return

        customer = payload.get("customer") or {}
        name = str(customer.get("name", "")).strip()
        phone = str(customer.get("phone", "")).strip()
        address = str(customer.get("address", "")).strip()
        items = payload.get("items") or []
        total = payload.get("total")

        if not name or not phone or not address or not isinstance(items, list):
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": "Missing fields"}).encode("utf-8"))
            return

        if not isinstance(total, int):
            try:
                total = int(total)
            except (TypeError, ValueError):
                total = 0

        created_at = datetime.now(timezone.utc).isoformat()
        items_json = json.dumps(items, ensure_ascii=True)

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO orders (name, phone, address, items_json, total, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (name, phone, address, items_json, total, created_at),
                )
        except sqlite3.Error:
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": "Database error"}).encode("utf-8"))
            return

        self._set_headers(HTTPStatus.CREATED)
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

    def handle_list_orders(self) -> None:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute(
                    """
                    SELECT id, name, phone, address, items_json, total, created_at
                    FROM orders
                    ORDER BY id DESC
                    LIMIT 50
                    """
                ).fetchall()
        except sqlite3.Error:
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": "Database error"}).encode("utf-8"))
            return

        orders = []
        for row in rows:
            orders.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "phone": row[2],
                    "address": row[3],
                    "items": json.loads(row[4]),
                    "total": row[5],
                    "created_at": row[6],
                }
            )

        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps({"orders": orders}).encode("utf-8"))

    def handle_admin_page(self) -> None:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute(
                    """
                    SELECT id, name, phone, address, items_json, total, created_at
                    FROM orders
                    ORDER BY id DESC
                    LIMIT 100
                    """
                ).fetchall()
        except sqlite3.Error:
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR, "text/plain; charset=utf-8")
            self.wfile.write(b"Database error")
            return

        orders = []
        for row in rows:
            orders.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "phone": row[2],
                    "address": row[3],
                    "items": json.loads(row[4]),
                    "total": row[5],
                    "created_at": row[6],
                }
            )

        self._set_headers(HTTPStatus.OK, "text/html; charset=utf-8")
        self.wfile.write(render_admin_page(orders))


def main() -> None:
    init_db()
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), RequestHandler)
    print(f"API ready on http://localhost:{port}")
    print("Admin dashboard: http://localhost:%s/admin (user: admin)" % port)
    server.serve_forever()


if __name__ == "__main__":
    main()
