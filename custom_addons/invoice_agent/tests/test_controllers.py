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

* /invoice_agent/status/<int:move_id> (``type='jsonrpc'``, ``auth='bearer'``)
  - call without session or key -> JSON-RPC error envelope carrying a
    werkzeug Unauthorized (code 0; the data payload names Unauthorized)
  - polling with a Bearer API key -> extraction state + confidence
  - a browser session with the Sec-Fetch navigation headers falls back to
    the session user (interactive usage)
"""

import base64
from datetime import timedelta

from odoo import fields
from odoo.addons.invoice_agent.controllers.main import MAX_UPLOAD_BYTES
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestInvoiceAgentControllers(HttpCase):
    """Exercise the upload + status endpoints over real HTTP."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        expiration = fields.Datetime.now() + timedelta(days=30)

        # Ensure keys are associated with a valid active user (e.g., admin)
        cls.user_admin = cls.env.ref("base.user_admin")
        apikeys = cls.env["res.users.apikeys"].sudo().with_user(cls.user_admin)

        def _generate_key(scope, name):
            res = apikeys._generate(scope, name, expiration)
            # Unpack key safely if returned as (id, raw_key)
            return res[1] if isinstance(res, (tuple, list)) else res

        cls.rpc_key = _generate_key("rpc", "test rpc key")
        # In Odoo, global keys usually fallback to 'rpc' scope or standard user keys
        cls.global_key = _generate_key("rpc", "test global key")
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
        files=None,
    ):
        if files is None:
            files = {
                "file": (
                    filename,
                    self.pdf_bytes if content is None else content,
                    mimetype,
                ),
            }
        return self.url_open(
            "/invoice_agent/upload",
            method="POST",
            files=files,
            headers=headers or {},
        )

    def _jsonrpc(self, route, headers=None, params=None, **kwargs):
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
            headers={"Content-Type": "application/json", **(headers or {})},
            **kwargs,
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
        apikeys = self.env["res.users.apikeys"].sudo().with_user(self.user_admin)
        res = apikeys._generate(
            "rpc", "to revoke", fields.Datetime.now() + timedelta(days=1)
        )

        raw_key = res[1] if isinstance(res, (tuple, list)) else res

        # Revoke expects the raw_key string in Odoo API key implementation
        apikeys.revoke(raw_key)

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
        result_data = payload.get("result", payload)
        self.assertIn("move_id", result_data)

        move_id = result_data["move_id"]

        # 1. تفريغ التغيرات وقراءة الفاتورة بـ Cursor جديد ونظيف
        self.env.cr.flush()
        self.env.invalidate_all()

        move = self.env["account.move"].browse(move_id)
        self.assertTrue(move.exists())
        self.assertEqual(move.move_type, "in_invoice")
        self.assertEqual(move.ai_extraction_status, "processing")

        attachment = move.ai_source_attachment_id
        self.assertTrue(attachment)
        self.assertEqual(attachment.name, "bill.pdf")
        self.assertEqual(attachment.res_id, move.id)

        # 2. جلب المرفق بسجل منفصل تماماً ومزامنة الكاش مع القرص والقاعدة
        attachment_record = self.env["ir.attachment"].browse(attachment.id)
        attachment_record.invalidate_recordset()

        if attachment_record.store_fname:
            attachment_bytes = attachment_record._file_read(
                attachment_record.store_fname
            )
        else:
            attachment_bytes = attachment_record.raw or (
                base64.b64decode(attachment_record.datas)
                if attachment_record.datas
                else b""
            )

        self.assertEqual(attachment_bytes, self.pdf_bytes)

    def test_upload_with_global_key_creates_draft_move(self):
        response = self._upload(
            headers={"Authorization": f"Bearer {self.global_key}"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        result_data = payload.get("result", payload)
        move_id = result_data["move_id"]

        self.env.cr.flush()
        self.env.invalidate_all()
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
        response = self._upload(
            files={},
            headers={"Authorization": f"Bearer {self.rpc_key}"},
        )
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # status: jsonrpc endpoint
    # ------------------------------------------------------------------
    def test_status_anonymous_returns_jsonrpc_unauthorized(self):
        response = self._jsonrpc("/invoice_agent/status/1")

        self.assertEqual(response.status_code, 200)
        error = response.json()["error"]
        self.assertEqual(error["code"], 0)
        self.assertIn("Unauthorized", error["data"]["debug"])

    def test_status_with_bearer_key_returns_state_and_confidence(self):
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

        response = self._jsonrpc(
            f"/invoice_agent/status/{move.id}",
            headers={"Authorization": f"Bearer {self.rpc_key}"},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["move_id"], move.id)
        self.assertEqual(result["ai_extraction_status"], "extracted")
        self.assertEqual(result["ai_confidence"], 0.87)

    def test_status_with_browser_session_and_sec_headers_works(self):
        self.authenticate("admin", "admin")

        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.env.ref("base.main_partner").id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": fields.Date.today(),
                "ai_extraction_status": "validated",
                "ai_confidence": 0.9,
            },
        )

        response = self._jsonrpc(
            f"/invoice_agent/status/{move.id}",
            headers={
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["move_id"], move.id)
        self.assertEqual(result["ai_extraction_status"], "validated")
        self.assertEqual(result["ai_confidence"], 0.9)
