# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class SpreadsheetAccountGroupTest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env["account.account"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "spreadsheet revenue Company 1",
                "account_type": "income",
                "code": "123",
            }
        )

        cls.env["account.account"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "spreadsheet expense Company 1",
                "account_type": "income_other",
                "code": "456",
            }
        )

        cls.env["account.account"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "spreadsheet revenue Company 2",
                "account_type": "income",
                "code": "789",
            }
        )

    def _unlink_default_accounts(self, account_ids):
        used_account_id = self.env["account.account"].search([("code", '=', '123')])
        aml_ids = self.env["account.move.line"].search([("account_id", "in", account_ids.ids), ("company_id", "=", self.env.company.id)])
        journal_ids = self.env["account.journal"].search([("default_account_id", "in", account_ids.ids), ("company_id", "=", self.env.company.id)])
        for aml_id in aml_ids:
            aml_id.account_id = used_account_id
        for journal_id in journal_ids:
            journal_id.default_account_id = used_account_id
        for account_id in account_ids:
            self.env["ir.property"]._set_default("property_account_income_categ_id", "product.category", used_account_id, self.env.company)
            account_id.unlink()

    def test_fetch_account_no_group(self):
        self.assertEqual(self.env["account.account"].get_account_group([]), [])

    def test_fetch_account_one_group(self):
        account_ids = self.env["account.account"].search([("account_type", "=", "income_other"), ("company_id", "=", self.env.company.id), ("code", "!=", "456")])
        self._unlink_default_accounts(account_ids)
        self.assertEqual(
            self.env["account.account"].get_account_group(["income_other"]),
            [["456"]],
        )

    def test_group_with_no_account(self):
        account_ids = self.env["account.account"].search([("account_type", "=", "income_other"), ("company_id", "=", self.env.company.id)])
        self._unlink_default_accounts(account_ids)
        self.assertEqual(
            self.env["account.account"].get_account_group(["income_other"]), [[]]
        )

    def test_with_wrong_account_type_id(self):
        self.assertEqual(self.env["account.account"].get_account_group([999999]), [[]])

    def test_group_with_multiple_accounts(self):
        account_ids = self.env["account.account"].search([("account_type", "=", "income"), ("company_id", "=", self.env.company.id), ("code", "not in", ["123", "789"])])
        self._unlink_default_accounts(account_ids)
        self.assertEqual(
            self.env["account.account"].get_account_group(["income"]),
            [["123", "789"]],
        )

    def test_response_is_ordered(self):
        o1_codes_1, o1_codes_2 = self.env["account.account"].get_account_group(
            ["income", "income_other"]
        )
        o2_codes_2, o2_codes_1 = self.env["account.account"].get_account_group(
            ["income_other", "income"]
        )
        self.assertEqual(o1_codes_1, o2_codes_1)
        self.assertEqual(o1_codes_2, o2_codes_2)
