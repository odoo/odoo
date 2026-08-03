#!/usr/bin/env python3
"""End-to-end client demo for the invoice_agent module over the live Odoo.

Walks the full machine-to-machine flow against an HTTPS Odoo 19 instance:

    1. POST /invoice_agent/upload        (multipart, Bearer API key)
    2. POST /invoice_agent/status/<id>   (JSON-RPC, Bearer API key)
    3. XML-RPC  /xmlrpc/2/object         execute_kw → search_read
    4. JSON-2   /json/2/account.move/read (raw named-kwargs body, Bearer key)

This is a *throwaway teaching script*: every secret (--key, --login) is a
command-line argument or environment variable — nothing is hard-coded.

Usage
-----
    KEY=my-api-key python scripts/client_demo.py \
        --host https://invoices.example.com \
        --database prod \
        --login admin \
        --pdf-file bill.pdf

The API key comes from Preferences -> Account Security -> New API Key
(a global key; scope NULL matches the ``scope='rpc'`` check used by both the
upload decorator and Odoo's ``_auth_method_bearer``).
"""

import argparse
import json
import os
import sys
import time
import xmlrpc.client

import requests

# ---------------------------------------------------------------------------
# Constants — mirror the server-side policy in controllers/main.py
# ---------------------------------------------------------------------------
FINAL_STATUSES = {"extracted", "validated", "failed"}
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 300
DEFAULT_TIMEOUT = 30

# Field names below are the REAL invoice_agent fields. The task brief mentions
# ``extraction_confidence``; the live model names it ``ai_confidence`` and the
# state field is ``ai_extraction_status`` (see models/account_move.py).
READ_FIELDS = [
    "name",
    "ai_extraction_status",
    "ai_confidence",
    "amount_total",
    "invoice_partner_display_name",
]
JSON2_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "invoice-agent-client-demo",
}


class ClientDemoError(RuntimeError):
    """Raised for any API failure so the script exits non-zero."""


# ---------------------------------------------------------------------------
# 1. Upload  (POST /invoice_agent/upload, multipart, Bearer key)
# ---------------------------------------------------------------------------
def upload_pdf(host, api_key, pdf_path):
    """Upload the PDF and return the created move id."""
    url = f"{host.rstrip('/')}/invoice_agent/upload"
    headers = {"Authorization": f"Bearer {api_key}"}
    filename = os.path.basename(pdf_path)

    with open(pdf_path, "rb") as handle:
        response = requests.post(
            url,
            headers=headers,
            files={"file": (filename, handle, "application/pdf")},
            timeout=DEFAULT_TIMEOUT,
        )

    if response.status_code != 201:
        raise ClientDemoError(
            f"upload failed: HTTP {response.status_code}:\n{response.text}"
        )

    # The upload route returns a JSON-RPC-style envelope:
    # {"jsonrpc": "2.0", "id": null, "result": {"move_id": ..., ...}}
    payload = response.json()
    result = payload.get("result") if isinstance(payload, dict) else None
    move_id = result.get("move_id") if isinstance(result, dict) else None
    if not move_id:
        raise ClientDemoError(f"upload response missing result.move_id: {payload}")

    print(f"  [upload] 201 — move_id={move_id} "
          f"ai_extraction_status={result.get('ai_extraction_status')}")
    return move_id


# ---------------------------------------------------------------------------
# 2. Poll status  (POST /invoice_agent/status/<id>, JSON-RPC, Bearer key)
# ---------------------------------------------------------------------------
def poll_status(host, api_key, move_id):
    """POST JSON-RPC until extraction finishes, then return the status dict."""
    url = f"{host.rstrip('/')}/invoice_agent/status/{move_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {"jsonrpc": "2.0", "method": "call", "id": 1, "params": {}}

    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        payload = response.json()

        # JSON-RPC error envelope: {"jsonrpc":"2.0","id":1,"error":{...}}
        if "error" in payload:
            raise ClientDemoError(
                f"status error: {payload['error'].get('code')} "
                f"{payload['error'].get('message')}"
            )
        result = payload.get("result", {})
        state = result.get("ai_extraction_status")
        print(f"  [status] move_id={move_id} ai_extraction_status={state} "
              f"ai_confidence={result.get('ai_confidence')}")

        if state in FINAL_STATUSES:
            return result
        time.sleep(POLL_INTERVAL_SECONDS)

    raise ClientDemoError(
        f"timed out after {POLL_TIMEOUT_SECONDS}s waiting for extraction on "
        f"move {move_id}"
    )


# ---------------------------------------------------------------------------
# 3. XML-RPC read  (authenticate with the API key in place of the password)
# ---------------------------------------------------------------------------
def xmlrpc_authenticate(host, database, login, api_key):
    """common.authenticate: the API key is passed as the 'password'."""
    common = xmlrpc.client.ServerProxy(
        f"{host.rstrip('/')}/xmlrpc/2/common",
        allow_none=True,
    )
    uid = common.authenticate(database, login, api_key, {})
    if not uid:
        raise ClientDemoError("XML-RPC authenticate() returned False — check "
                              "login and API key")
    print(f"  [xmlrpc] authenticated as '{login}' -> uid={uid}")
    return uid


def xmlrpc_read_bills(host, database, uid, api_key, move_id):
    """object.execute_kw → search_read with the API key as password."""
    models = xmlrpc.client.ServerProxy(
        f"{host.rstrip('/')}/xmlrpc/2/object",
        allow_none=True,
    )
    records = models.execute_kw(
        database,
        uid,
        api_key,
        "account.move",
        "search_read",
        [[("id", "=", move_id)]],
        {
            "fields": READ_FIELDS,
            "limit": 5,
        },
    )
    if not records:
        raise ClientDemoError(f"XML-RPC search_read returned no record for move {move_id}")
    print(f"  [xmlrpc] search_read -> {json.dumps(records, indent=2, default=str)}")
    return records


# ---------------------------------------------------------------------------
# 4. JSON-2 read  (POST /json/2/account.move/read — named kwargs, raw value back)
# ---------------------------------------------------------------------------
def json2_read_move(host, database, api_key, move_id):
    """Odoo 19 external API: /json/2/<model>/<method> with named arguments.

    The request body holds all method kwargs (``ids``, ``fields``, ...) — there
    are NO positional args and NO JSON-RPC envelope; the response body is the
    raw return value of ``read()``.
    """
    url = f"{host.rstrip('/')}/json/2/account.move/read"
    headers = {
        **JSON2_HEADERS,
        "Authorization": f"bearer {api_key}",
        "X-Odoo-Database": database,
    }
    body = {
        "ids": [move_id],
        "fields": READ_FIELDS,
    }
    response = requests.post(url, headers=headers, json=body, timeout=DEFAULT_TIMEOUT)

    if response.status_code != 200:
        raise ClientDemoError(
            f"/json/2 read failed: HTTP {response.status_code}\n{response.text}"
        )

    records = response.json()
    print(f"  [json/2] read -> {json.dumps(records, indent=2, default=str)}")
    return records


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="invoice_agent client demo: upload -> poll -> read "
                    "(XML-RPC and /json/2).",
    )
    parser.add_argument("--host", required=True,
                        help="Base URL, e.g. https://invoices.example.com")
    parser.add_argument("--database", required=True, help="Odoo database name")
    parser.add_argument("--key", default=os.environ.get("KEY", ""),
                        help="API key (default: $KEY; never commit it)")
    parser.add_argument("--login", default="admin",
                        help="XML-RPC login (default: admin)")
    parser.add_argument("--pdf-file", required=True,
                        help="Path to the PDF invoice to upload")
    parser.add_argument("--poll-interval", type=float, default=POLL_INTERVAL_SECONDS,
                        help=f"Seconds between status polls (default: {POLL_INTERVAL_SECONDS})")
    return parser.parse_args(argv)


def main(argv=None):
    global POLL_INTERVAL_SECONDS
    args = parse_args(argv)
    POLL_INTERVAL_SECONDS = args.poll_interval

    if not args.key:
        raise SystemExit("error: an API key is required via --key or $KEY")

    if not os.path.exists(args.pdf_file):
        raise SystemExit(f"error: PDF file not found: {args.pdf_file}")

    print(f"== invoice_agent client demo against {args.host} ==")
    move_id = upload_pdf(args.host, args.key, args.pdf_file)
    status = poll_status(args.host, args.key, move_id)
    if status.get("ai_extraction_status") == "failed":
        print("  !! extraction failed on the server; final state follows anyway")

    print("\n-- XML-RPC --")
    uid = xmlrpc_authenticate(args.host, args.database, args.login, args.key)
    xmlrpc_read_bills(args.host, args.database, uid, args.key, move_id)

    print("\n-- Odoo 19 /json/2 --")
    json2_read_move(args.host, args.database, args.key, move_id)

    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except ClientDemoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
