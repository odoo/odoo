# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestReconcileUiBridge(TransactionCase):
    """ตรวจว่า bridge เชื่อม OD19 core เข้ากับ OCA reconcile UI ได้จริง."""

    def test_oca_reconcile_model_is_available(self):
        """โมเดลกลางของ OCA ต้องมีใน registry เมื่อ bridge ถูกติดตั้ง."""
        self.assertIn("account.reconcile.abstract", self.env.registry)

    def test_oca_reconcile_menu_is_available(self):
        """เมนู Reconcile ของ OCA ต้องอยู่ใต้ Accounting ▸ Entries."""
        menu = self.env.ref(
            "account_reconcile_oca.account_account_reconcile_menu",
            raise_if_not_found=False,
        )
        self.assertTrue(menu, "ไม่พบเมนู Reconcile ของ OCA")
        self.assertEqual(
            menu.parent_id,
            self.env.ref("account.menu_finance_entries"),
        )

    def test_core_module_does_not_depend_on_oca(self):
        """OD19 core ต้องไม่ผูกกับ OCA แบบ hard dependency อีกต่อไป."""
        deps = (
            self.env["ir.module.module.dependency"]
            .search([("module_id.name", "=", "od19_accounting_features")])
            .mapped("name")
        )
        self.assertNotIn("account_reconcile_oca", deps)

    def test_bridge_is_auto_installable_and_installed(self):
        """bridge ต้องเป็น auto_install และถูกติดตั้งเมื่อพร้อมทั้งสองฝ่าย."""
        bridge = self.env["ir.module.module"].search(
            [("name", "=", "od19_accounting_reconcile_ui")], limit=1
        )
        self.assertTrue(bridge, "ไม่พบโมดูล bridge ในทะเบียน")
        self.assertTrue(bridge.auto_install)
        self.assertEqual(bridge.state, "installed")
