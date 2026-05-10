#!/usr/bin/env python3
# Sarvam AI proxy — flattens AI SDK content-parts arrays to plain strings.
# Usage: python3 sarvam_proxy.py [port]
# Point clients at http://localhost:4040 (proxy adds /v1 automatically)

import http.server
import urllib.request
import urllib.error
import json
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4040
UPSTREAM = "https://api.sarvam.ai"

MODELS = [
    {"id": "sarvam-105b", "object": "model", "created": 1700000000, "owned_by": "sarvam"},
    {"id": "sarvam-30b", "object": "model", "created": 1700000001, "owned_by": "sarvam"},
    {"id": "sarvam-m", "object": "model", "created": 1700000002, "owned_by": "sarvam"},
]


def upstream_path(client_path):
    """Prepend /v1 when the client omits it."""
    return client_path if client_path.startswith("/v1/") else f"/v1{client_path}"


def flatten_content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for part in value:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    parts.append(part.get("text", ""))
                elif part.get("type") == "image_url":
                    parts.append("[image]")
        return "".join(parts).strip()
    return str(value) if value is not None else ""


def normalize_body(body):
    if not isinstance(body.get("messages"), list):
        return body
    return {
        **body,
        "messages": [
            {**msg, "content": flatten_content(msg["content"])}
            if "content" in msg else msg
            for msg in body["messages"]
        ],
    }


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[proxy] {self.address_string()} — {fmt % args}")

    def do_GET(self):
        if self.path in ("/models", "/v1/models"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"object": "list", "data": MODELS}).encode())
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        # Retrieve the API key sent by the client
        auth_header = self.headers.get("Authorization")

        # Optional fallback to local environment variable if client provides no header
        if not auth_header:
            env_key = os.environ.get("SARVAM_API_KEY")
            if env_key:
                auth_header = f"Bearer {env_key}"

        try:
            body = normalize_body(json.loads(raw))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"invalid json")
            return

        payload = json.dumps(body).encode()

        # Forward original client headers, prioritizing their Authorization
        request_headers = {
            "Content-Type": "application/json",
        }
        if auth_header:
            request_headers["Authorization"] = auth_header

        upstream_req = urllib.request.Request(
            f"{UPSTREAM}{upstream_path(self.path)}",
            data=payload,
            headers=request_headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(upstream_req, timeout=60) as resp:
                self.send_response(resp.status)
                for key, val in resp.headers.items():
                    # Strip hop-by-hop headers and let urllib handle content-length
                    if key.lower() not in ("transfer-encoding", "connection", "content-length"):
                        self.send_header(key, val)
                self.end_headers()

                while chunk := resp.read(4096):
                    self.wfile.write(chunk)
                    self.wfile.flush()

        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            for key, val in e.headers.items():
                if key.lower() not in ("transfer-encoding", "connection", "content-length"):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(err_body)

        except Exception as e:
            print(f"upstream error: {e}", file=sys.stderr)
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b"upstream error")


if __name__ == "__main__":
    # Using ThreadingHTTPServer to handle multiple concurrent client requests
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"Sarvam proxy listening on http://127.0.0.1:{PORT}")
    print(f"Forwarding to {UPSTREAM}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")