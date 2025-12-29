import json
import html
import mimetypes
import os
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, parse_qs
import base64


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR)))
DB_PATH = Path(os.environ.get("DB_PATH", str(DATA_DIR / "orders.db")))
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
        safe_items = html.escape(items)
        rows.append(
            f"""
            <tr>
              <td>{order["id"]}</td>
              <td>{html.escape(order["name"])}</td>
              <td>{html.escape(order["phone"])}</td>
              <td>{html.escape(order["address"])}</td>
              <td>{safe_items}</td>
              <td>{order["total"]} TND</td>
              <td>{order["created_at"]}</td>
              <td>
                <button class="action-btn" type="button" data-delete="{order["id"]}">
                  Supprimer
                </button>
              </td>
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
        .action-btn {{
          background: #1b1916;
          color: #fff;
          border: none;
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 0.75rem;
          letter-spacing: 0.06rem;
          text-transform: uppercase;
          cursor: pointer;
        }}
        .modal-overlay {{
          position: fixed;
          inset: 0;
          background: rgba(10, 8, 6, 0.5);
          display: none;
          align-items: center;
          justify-content: center;
          z-index: 100;
        }}
        .modal {{
          background: #fff;
          border-radius: 16px;
          padding: 20px;
          max-width: 360px;
          width: calc(100% - 32px);
          box-shadow: 0 20px 50px rgba(10, 8, 6, 0.2);
          display: grid;
          gap: 14px;
        }}
        .modal h2 {{
          margin: 0;
          font-size: 1.1rem;
        }}
        .modal-actions {{
          display: flex;
          gap: 10px;
          justify-content: flex-end;
        }}
        .btn-cancel {{
          background: #f4efe7;
          border: none;
          padding: 8px 12px;
          border-radius: 999px;
          cursor: pointer;
        }}
        .btn-danger {{
          background: #1b1916;
          color: #fff;
          border: none;
          padding: 8px 12px;
          border-radius: 999px;
          cursor: pointer;
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
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows) if rows else '<tr><td colspan="8">Aucune commande.</td></tr>'}
        </tbody>
      </table>
      <div class="modal-overlay" id="confirmModal" aria-hidden="true">
        <div class="modal" role="dialog" aria-modal="true">
          <h2>Supprimer la commande ?</h2>
          <p>Cette action est definitive.</p>
          <form method="post" action="/admin/delete" id="deleteForm">
            <input type="hidden" name="id" id="deleteId" value="" />
            <div class="modal-actions">
              <button class="btn-cancel" type="button" id="cancelDelete">Annuler</button>
              <button class="btn-danger" type="submit">Supprimer</button>
            </div>
          </form>
        </div>
      </div>
      <script>
        const modal = document.getElementById("confirmModal");
        const deleteId = document.getElementById("deleteId");
        const cancelDelete = document.getElementById("cancelDelete");

        document.querySelectorAll("[data-delete]").forEach((btn) => {{
          btn.addEventListener("click", () => {{
            deleteId.value = btn.dataset.delete;
            modal.style.display = "flex";
            modal.setAttribute("aria-hidden", "false");
          }});
        }});

        const closeModal = () => {{
          modal.style.display = "none";
          modal.setAttribute("aria-hidden", "true");
          deleteId.value = "";
        }};

        cancelDelete.addEventListener("click", closeModal);
        modal.addEventListener("click", (event) => {{
          if (event.target === modal) closeModal();
        }});
      </script>
    </body>
    </html>
    """
    return html.encode("utf-8")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
        if self.path.startswith("/admin/delete"):
            if not is_authorized(self):
                self.send_response(HTTPStatus.UNAUTHORIZED)
                self.send_header("WWW-Authenticate", 'Basic realm="Admin"')
                self.end_headers()
                return
            self.handle_delete_order()
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

    def handle_delete_order(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b""
        data = parse_qs(raw_body.decode("utf-8"))
        order_id = data.get("id", [""])[0]
        try:
            order_id_int = int(order_id)
        except (TypeError, ValueError):
            self._set_headers(HTTPStatus.BAD_REQUEST, "text/plain; charset=utf-8")
            self.wfile.write(b"Invalid order id")
            return

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM orders WHERE id = ?", (order_id_int,))
        except sqlite3.Error:
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR, "text/plain; charset=utf-8")
            self.wfile.write(b"Database error")
            return

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/admin")
        self.end_headers()


def main() -> None:
    init_db()
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), RequestHandler)
    print(f"API ready on http://localhost:{port}")
    print("Admin dashboard: http://localhost:%s/admin (user: admin)" % port)
    server.serve_forever()


if __name__ == "__main__":
    main()
