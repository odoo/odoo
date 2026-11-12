# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from psycopg2 import IntegrityError

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRetentionPolicy(TransactionCase):

    def test_create_policy(self):
        policy = self.env["od19.document.retention.policy"].create({
            "name": "บัญชี 5 ปี",
            "duration_month": 60,
            "action": "delete",
        })
        self.assertEqual(policy.duration_month, 60)

    def test_duration_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env["od19.document.retention.policy"].create({
                    "name": "ผิด", "duration_month": 0, "action": "review",
                })


@tagged("post_install", "-at_install")
class TestDocumentCategory(TransactionCase):

    def test_complete_name(self):
        parent = self.env["od19.document.category"].create({"name": "จัดซื้อ", "code": "TST_PUR"})
        child = self.env["od19.document.category"].create({
            "name": "ใบสั่งซื้อ", "code": "TST_PUR_PO", "parent_id": parent.id,
        })
        self.assertEqual(child.complete_name, "จัดซื้อ / ใบสั่งซื้อ")

    def test_code_unique(self):
        self.env["od19.document.category"].create({"name": "A", "code": "DUP"})
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env["od19.document.category"].create({"name": "B", "code": "DUP"})

    def test_no_parent_cycle(self):
        a = self.env["od19.document.category"].create({"name": "A", "code": "CYC_A"})
        b = self.env["od19.document.category"].create({"name": "B", "code": "CYC_B", "parent_id": a.id})
        # Odoo core กัน cycle ให้แล้วผ่าน _parent_store_update (UserError "Recursion Detected.")
        with self.assertRaises(UserError):
            with self.cr.savepoint():
                a.parent_id = b.id

