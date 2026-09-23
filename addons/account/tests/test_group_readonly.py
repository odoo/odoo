from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestAccountGroupReadonly(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_readonly = cls.env.ref("account.group_account_readonly")
        cls.user_readonly = cls.env["res.users"].create(
            {
                "name": "Test Account Readonly",
                "login": "test_account_readonly",
                "group_ids": [Command.set([cls.group_readonly.id])],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Readonly Customer"})
        cls.move = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "line", "quantity": 1, "price_unit": 10})
                ],
            }
        )

    def test_group_is_the_lowest_rung_of_the_accounting_privilege(self):
        privilege = self.env.ref("account.res_groups_privilege_accounting")
        invoicing = self.env.ref("account.group_account_invoice")
        self.assertEqual(self.group_readonly.privilege_id, privilege)
        self.assertLess(self.group_readonly.sequence, invoicing.sequence)
        self.assertIn(self.env.ref("base.group_user"), self.group_readonly.implied_ids)

    def test_every_rung_above_implies_readonly(self):
        for xmlid in (
            "account.group_account_invoice",
            "account.group_account_basic",
            "account.group_account_user",
            "account.group_account_manager",
        ):
            self.assertIn(
                self.group_readonly,
                self.env.ref(xmlid).all_implied_ids,
                f"{xmlid} must imply Read-only",
            )

    def test_readonly_reads_and_cannot_write_moves(self):
        move = self.move.with_user(self.user_readonly)
        move.read(["name", "amount_total"])
        move.line_ids.read(["debit", "credit"])
        with self.assertRaises(AccessError):
            move.write({"ref": "nope"})
        with self.assertRaises(AccessError):
            self.env["account.move"].with_user(self.user_readonly).create(
                {"move_type": "out_invoice", "partner_id": self.partner.id}
            )

    def test_acl_rows_grant_read_only(self):
        rows = self.env["ir.access"].search(
            [("group_id", "=", self.group_readonly.id), ("kind", "=", "permission")]
        )
        self.assertTrue(rows)
        writable = [
            row.model_id.model
            for row in rows
            if row.for_write or row.for_create or row.for_unlink
        ]
        self.assertFalse(writable, f"these rows are not read-only: {sorted(writable)}")

    def test_readonly_sees_journal_entries_and_reports(self):
        visible = (
            self.env["ir.ui.menu"].with_user(self.user_readonly)._get_visible_menu_ids()
        )
        for xmlid in ("account.menu_finance_entries", "account.menu_finance_reports"):
            self.assertIn(self.env.ref(xmlid).id, visible, xmlid)
