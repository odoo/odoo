# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttachmentMetadata(TransactionCase):

    def test_defaults(self):
        att = self.env["ir.attachment"].create({
            "name": "a.txt", "datas": base64.b64encode(b"hello"),
        })
        self.assertEqual(att.od19_origin, "external")
        self.assertEqual(att.od19_confidentiality, "internal")
        self.assertEqual(att.od19_index_state, "none")

    def test_retention_until_computed(self):
        policy = self.env["od19.document.retention.policy"].create({
            "name": "5 ปี", "duration_month": 60, "action": "delete",
        })
        att = self.env["ir.attachment"].create({
            "name": "b.txt",
            "datas": base64.b64encode(b"x"),
            "od19_doc_date": datetime.date(2026, 1, 31),
            "od19_retention_policy_id": policy.id,
        })
        self.assertEqual(att.od19_retention_until, datetime.date(2031, 1, 31))

    def test_duplicate_count(self):
        payload = base64.b64encode(b"same-bytes")
        a1 = self.env["ir.attachment"].create({"name": "d1.txt", "datas": payload})
        a2 = self.env["ir.attachment"].create({"name": "d2.txt", "datas": payload})
        self.assertEqual(a1.checksum, a2.checksum)
        self.assertEqual(a1.od19_duplicate_count, 1)
