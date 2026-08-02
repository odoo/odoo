"""Negative and positive HttpCase tests for the invoice_agent endpoints.

Covered here:

* /invoice_agent/upload (``type='http'``, ``auth='none'``, ``csrf=False``)
  - 401 JSON when the Bearer token is missing
  - 401 JSON when the token is invalid / revoked
  - 401 JSON when the token has the wrong scope
  - 201 + move_id with a valid global or ``rpc``-scoped API key
  - 400 for oversized payloads (nothing persisted)
  - 400 for non-PDF mimetypes (nothing persisted)
  - 400 when the ``file`` part is missing

* /invoice_agent/status/<int:move_id> (``type='jsonrpc'``, ``auth='user'``)
  - anonymous call -> JSON-RPC error envelope code 100 (SessionExpired)
  - authenticated call -> extraction state + confidence
"""

import base64
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

from odoo.addons.invoice_agent.controllers.main import MAX_UPLOAD_BYTES


@tagged("post_install", "-at_install")
class TestInvoiceAgentControllers(HttpCase):
    """Exercise the upload + status endpoints over real HTTP."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        expiration = fields.Datetime.now() + timedelta(days=30)

        apikeys = cls.env["res.users.apikeys"].sudo()

        def _generate_key(scope, name):
            # _generate returns a tuple: (key_id, raw_key_string)
            return apikeys._generate(scope, name, expiration)[1]

        cls.rpc_key = _generate_key("rpc", "test rpc key")
        cls.global_key = _generate_key("base.api_key_global", "test global key")
        cls.wrong_scope_key = _generate_key("website", "test website key")

        cls.pdf_bytes = b"%PDF-1.4 fake vendor bill for controller tests"

        purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase")],
            limit=1,
        )
        if not purchase_journal:
            purchase_journal = cls.env["account.journal"].create(
                {
                    "name": "Test Purchase Journal",
                    "type": "purchase",
                    "code": "TPJ",
                },
            )
        cls.purchase_journal = purchase_journal

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _upload(
        self,
        headers=None,
        filename="bill.pdf",
        content=None,
        mimetype="application/pdf",
    ):
        return self.url_open(
            "/invoice_agent/upload",
            method="POST",
            files={
                "file": (
                    filename,
                    self.pdf_bytes if content is None else content,
                    mimetype,
                ),
            },
            headers=headers or {},
        )

    def _jsonrpc(self, route, authenticated=False, params=None):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": params or {},
        }
        return self.url_open(
            route,
            method="POST",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    # ------------------------------------------------------------------
    # upload: authentication failures -> JSON 401
    # ------------------------------------------------------------------
    def test_upload_without_token_returns_json_401(self):
        response = self._upload()

        self.assertEqual(response.status_code, 401)
        self.assertIn("application/json", response.headers.get("Content-Type", ""))
        self.assertIn("error", response.json())

    def test_upload_with_invalid_token_returns_json_401(self):
        response = self._upload(
            headers={"Authorization": "Bearer not-a-real-api-key"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_upload_with_wrong_scope_token_returns_json_401(self):
        response = self._upload(
            headers={"Authorization": f"Bearer {self.wrong_scope_key}"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_upload_rejects_after_key_revocation(self):
        res = (
            self.env["res.users.apikeys"]
            .sudo()
            ._generate("rpc", "to revoke", fields.Datetime.now() + timedelta(days=1))
        )
        key_id, raw_key = res
 
        self.env["res.users.apikeys"].sudo().revoke(key_id)

        response = self._upload(
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------
    # upload: happy path
    # ------------------------------------------------------------------
    def test_upload_with_rpc_key_creates_draft_move(self):
        response = self._upload(
            headers={"Authorization": f"Bearer {self.rpc_key}"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn("move_id", payload["result"])

        move = self.env["account.move"].browse(payload["result"]["move_id"])
        self.assertTrue(move.exists())
        self.assertEqual(move.move_type, "in_invoice")
        # The extraction state machine must have picked it up.
        self.assertEqual(move.ai_extraction_status, "processing")
        # The PDF was stored and linked to the bill.
        self.assertTrue(move.ai_source_attachment_id)
        self.assertEqual(move.ai_source_attachment_id.name, "bill.pdf")
        self.assertEqual(move.ai_source_attachment_id.res_id, move.id)
        # Binary fields are read back base64-encoded (see Stream.from_binary_field
        # in odoo/http.py) — decode before comparing against the raw bytes.
        self.assertEqual(
            base64.b64decode(move.ai_source_attachment_id.raw),
            self.pdf_bytes,
        )

    def test_upload_with_global_key_creates_draft_move(self):
        response = self._upload(
            headers={"Authorization": f"Bearer {self.global_key}"},
        )

        self.assertEqual(response.status_code, 201)
        move_id = response.json()["result"]["move_id"]
        self.assertTrue(self.env["account.move"].browse(move_id).exists())

    # ------------------------------------------------------------------
    # upload: input validation (before ir.attachment is touched)
    # ------------------------------------------------------------------
    def test_upload_rejects_oversized_file_without_persisting(self):
        oversized = b"x" * (MAX_UPLOAD_BYTES + 1024)

        response = self._upload(
            filename="huge.pdf",
            content=oversized,
            headers={"Authorization": f"Bearer {self.rpc_key}"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.env["ir.attachment"].search_count([("name", "=", "huge.pdf")]),
            0,
        )

    def test_upload_rejects_non_pdf_mimetype_without_persisting(self):
        response = self._upload(
            filename="bill.txt",
            content=b"just some text",
            mimetype="text/plain",
            headers={"Authorization": f"Bearer {self.rpc_key}"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.env["ir.attachment"].search_count([("name", "=", "bill.txt")]),
            0,
        )

    def test_upload_without_file_part_returns_400(self):
        # To correctly simulate a multipart request with a missing file part,
        # we must explicitly set the Content-Type. Otherwise, url_open with
        # empty `files` sends a request with no body, causing the auth
        # check to fail with 401 before the file part validation is reached.
        response = self.url_open(
            "/invoice_agent/upload",
            method="POST",
            files={},
            headers={"Authorization": f"Bearer {self.rpc_key}"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # status: jsonrpc endpoint
    # ------------------------------------------------------------------
    def test_status_anonymous_returns_jsonrpc_session_expired(self):
        response = self._jsonrpc("/invoice_agent/status/1")

        # JSON-RPC 2.0: transport errors are reported as 200 with an
        # error envelope. SessionExpiredException maps to code 100.
        self.assertEqual(response.status_code, 200)
        error = response.json()["error"]
        self.assertEqual(error["code"], 100)

    def test_status_authenticated_returns_state_and_confidence(self):
        self.authenticate("admin", "admin")

        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.env.ref("base.main_partner").id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": fields.Date.today(),
                "ai_extraction_status": "extracted",
                "ai_confidence": 0.87,
            },
        )

        response = self._jsonrpc(f"/invoice_agent/status/{move.id}")

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["move_id"], move.id)
        self.assertEqual(result["ai_extraction_status"], "extracted")
        self.assertEqual(result["ai_confidence"], 0.87)
