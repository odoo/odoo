from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestQboStandardAccount(TransactionCase):

    def test_import_chart_rows_creates_hierarchy(self):
        rows = [
            {
                "code": "10000",
                "description": "ASSET",
                "long_description": "Header",
                "type": "Header",
                "category": "Asset",
                "fs_mapping": "Balance Sheet",
                "parent_code": "",
                "normal_balance": "Debit",
                "tags": "",
                "default_vendors": "",
                "regulatory_mapping": "",
                "start_date": "",
                "end_date": "",
                "notes": "",
                "subcategory": "",
                "cash_flow_classification": "",
                "cost_center": "",
                "GAAP_classification": "Asset",
                "detailed_description": "Header",
            },
            {
                "code": "10100",
                "description": "Operating Cash",
                "long_description": "Detail",
                "type": "Detail",
                "category": "Asset",
                "fs_mapping": "Balance Sheet",
                "parent_code": "10000",
                "normal_balance": "Debit",
                "tags": "cash",
                "default_vendors": "",
                "regulatory_mapping": "",
                "start_date": "",
                "end_date": "",
                "notes": "",
                "subcategory": "Current Asset - Cash and Cash Equivalents",
                "cash_flow_classification": "Operating Activities",
                "cost_center": "CC-1000",
                "GAAP_classification": "US-GAAP Asset",
                "detailed_description": "Cash account",
            },
        ]
        stats = self.env["qbo.standard.account"].import_chart_rows(rows)

        header = self.env["qbo.standard.account"].search(
            [("code", "=", "10000"), ("entry_type", "=", "header")],
        )
        detail = self.env["qbo.standard.account"].search(
            [("code", "=", "10100"), ("entry_type", "=", "detail")],
        )
        self.assertEqual(stats["created"], 2)
        self.assertEqual(detail.parent_id, header)
        self.assertEqual(detail.odoo_account_type, "asset_cash")

    def test_bridge_rule_inherits_standard_account_fields(self):
        standard = self.env["qbo.standard.account"].create(
            {
                "code": "40010",
                "description": "Consulting Revenue",
                "entry_type": "detail",
                "category": "Revenue",
                "normal_balance": "credit",
                "odoo_account_type": "income",
            },
        )
        rule = self.env["qbo.account.bridge.rule"].create(
            {
                "standard_account_id": standard.id,
                "match_name": "Consulting Income",
                "canonical_code": "temp",
                "canonical_name": "temp",
                "canonical_account_type": "income",
            },
        )

        self.assertEqual(rule.canonical_code, "40010")
        self.assertEqual(rule.canonical_name, "Consulting Revenue")
        self.assertEqual(rule.canonical_account_type, "income")

    def test_sync_wizard_creates_company_account_and_pushes(self):
        standard = self.env["qbo.standard.account"].create(
            {
                "code": "61010",
                "description": "Office Supplies",
                "entry_type": "detail",
                "category": "Expense",
                "normal_balance": "debit",
                "odoo_account_type": "expense",
            },
        )
        realm = self.env["qbo.realm"].create(
            {
                "name": "Realm",
                "realm_id": "123",
                "client_id": "cid",
                "client_secret": "secret",
                "state": "connected",
            },
        )
        mapping = self.env["qbo.company.mapping"].create(
            {
                "company_id": self.env.company.id,
                "realm_id": realm.id,
            },
        )
        wizard = self.env["qbo.standard.account.sync.wizard"].create(
            {
                "standard_account_id": standard.id,
                "mapping_ids": [(6, 0, [mapping.id])],
            },
        )

        with patch(
            "odoo.addons.qbo_bridge.services.qbo_sync_engine.QBOSyncEngine.push_account_record",
        ) as push_account:
            wizard.action_sync()

        account = self.env["account.account"].search(
            [
                ("company_ids", "=", self.env.company.id),
                ("qbo_standard_account_id", "=", standard.id),
            ],
            limit=1,
        )
        self.assertTrue(account)
        self.assertEqual(account.code, "61010")
        self.assertEqual(account.name, "Office Supplies")
        push_account.assert_called_once()

    def test_sync_detail_accounts_to_company_creates_native_chart_accounts(self):
        standard = self.env["qbo.standard.account"].create(
            {
                "code": "12010",
                "description": "Accounts Receivable",
                "entry_type": "detail",
                "category": "Asset",
                "normal_balance": "debit",
                "odoo_account_type": "asset_receivable",
            },
        )

        stats = self.env["qbo.standard.account"].sync_detail_accounts_to_company(
            self.env.company,
            update_existing=True,
        )

        account = self.env["account.account"].search(
            [
                ("company_ids", "=", self.env.company.id),
                ("qbo_standard_account_id", "=", standard.id),
            ],
            limit=1,
        )
        self.assertTrue(account)
        self.assertEqual(stats["created"], 1)
        self.assertEqual(account.name, "Accounts Receivable")
