from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import subprocess


class Handler(BaseHTTPRequestHandler):
    def make_response(self, code, message):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(message.encode())

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        token = qs.get("token", [None])[0]

        if not token or not token.startswith("tskey-"):
            self.make_response(400, "Invalid or missing token")
            return

        try:
            subprocess.run(
                ["sudo", "tailscale", "up", f"--authkey={token}", "--hostname=emergency-access", "--timeout=10s"],
                check=True,
            )
            subprocess.run(
                ['sudo', 'cp', '-r', '/var/lib/tailscale/', '/root_bypass_ramdisks/var/lib/tailscale/'],
                check=True,
            )
            self.make_response(200, "Remote Debug is enabled, Odoo support team can now access the device.")
        except subprocess.CalledProcessError:
            self.make_response(
                500,
                "Remote Debug activation failed, please check the token, your internet connection and try again."
            )


HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
