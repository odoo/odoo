"""Integration tests for QBOSyncEngine.

Uses Odoo TransactionCase so models are available, but mocks QBOApiClient
so no live QBO credentials are required.

Run:
    ./odoo-bin -c deploy/odoo/kodoo.dev-host.local.conf -d ktest \
        --test-enable -i qbo_bridge --stop-after-init
"""
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase


class TestQBOSyncEngineAccounts(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env["res.company"].create({
            "name": "Test Umbrella Corp",
        })
        self.realm = self.env["qbo.realm"].create({
            "name": "Test QBO Realm",
            "realm_id": "123456789",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "state": "connected",
        })
        self.mapping = self.env["qbo.company.mapping"].create({
            "company_id": self.company.id,
            "realm_id": self.realm.id,
            "sync_accounts": True,
            "sync_partners": False,
            "sync_invoices": False,
            "sync_payments": False,
            "sync_journal_entries": False,
            "sync_products": False,
        })

    def _make_engine(self):
        from ..services.qbo_sync_engine import QBOSyncEngine
        engine = QBOSyncEngine(self.env, self.mapping)
        engine.client = MagicMock()
        return engine

    def test_pull_new_account_creates_odoo_record(self):
        engine = self._make_engine()
        qbo_accounts = [
            {
                "Id": "QBO-ACC-001",
                "SyncToken": "0",
                "Name": "Operating Cash",
                "AccountType": "Bank",
                "Active": True,
                "MetaData": {"LastUpdatedTime": "2024-01-01T00:00:00-00:00"},
            },
        ]
        engine._upsert_accounts(qbo_accounts, direction="pull")

        acc = self.env["account.account"].with_company(self.company).search([
            ("qbo_id", "=", "QBO-ACC-001"),
            ("company_ids", "=", self.company.id),
        ])
        self.assertTrue(acc, "Expected account.account to be created from QBO pull")
        self.assertEqual(acc.name, "Operating Cash")

    def test_pull_existing_account_updates_name(self):
        # Pre-create account with qbo_id
        existing = self.env["account.account"].with_company(self.company).create({
            "name": "Old Name",
            "code": "1001",
            "account_type": "asset_cash",
            "qbo_id": "QBO-ACC-002",
            "company_ids": [(4, self.company.id)],
        })
        engine = self._make_engine()
        qbo_accounts = [
            {
                "Id": "QBO-ACC-002",
                "SyncToken": "1",
                "Name": "Updated Cash Name",
                "AccountType": "Bank",
                "Active": True,
                "MetaData": {"LastUpdatedTime": "2024-01-01T00:00:00-00:00"},
            },
        ]
        engine._upsert_accounts(qbo_accounts, direction="pull")
        self.assertEqual(existing.name, "Updated Cash Name")

    def test_conflict_detected_creates_conflict_record(self):
        """When both sides changed since last sync, a conflict is created."""
        import datetime

        last_sync = datetime.datetime(2024, 1, 1, 0, 0, 0)
        self.mapping.write({"last_sync_accounts": last_sync})

        # Pre-create account modified AFTER last_sync
        existing = self.env["account.account"].with_company(self.company).create({
            "name": "Disputed Account",
            "code": "1002",
            "account_type": "asset_cash",
            "qbo_id": "QBO-ACC-003",
            "company_ids": [(4, self.company.id)],
        })
        # Force write_date > last_sync
        self.env.cr.execute(
            "UPDATE account_account SET write_date = %s WHERE id = %s",
            (datetime.datetime(2024, 6, 1), existing.id),
        )

        engine = self._make_engine()
        qbo_accounts = [
            {
                "Id": "QBO-ACC-003",
                "SyncToken": "2",
                "Name": "QBO Changed Name",
                "AccountType": "Bank",
                "Active": True,
                # QBO also modified after last_sync
                "MetaData": {"LastUpdatedTime": "2024-06-02T00:00:00-00:00"},
            },
        ]
        engine._upsert_accounts(qbo_accounts, direction="pull")

        conflict = self.env["qbo.conflict"].search([
            ("qbo_id", "=", "QBO-ACC-003"),
            ("mapping_id", "=", self.mapping.id),
        ])
        self.assertTrue(conflict, "Expected a conflict record to be created")
        self.assertEqual(conflict.status, "pending")

    def test_sync_log_written_on_success(self):
        engine = self._make_engine()
        qbo_accounts = [
            {
                "Id": "QBO-ACC-004",
                "SyncToken": "0",
                "Name": "Log Test Account",
                "AccountType": "Expense",
                "Active": True,
                "MetaData": {"LastUpdatedTime": "2024-01-01T00:00:00-00:00"},
            },
        ]
        engine._upsert_accounts(qbo_accounts, direction="pull")

        log = self.env["qbo.sync.log"].search([
            ("qbo_id", "=", "QBO-ACC-004"),
            ("mapping_id", "=", self.mapping.id),
        ])
        self.assertTrue(log)
        self.assertEqual(log.status, "success")
        self.assertEqual(log.direction, "pull")

    def test_push_new_account_calls_api(self):
        engine = self._make_engine()
        engine.client.create_account.return_value = {"Id": "QBO-NEW-001", "SyncToken": "0"}

        new_acc = self.env["account.account"].with_company(self.company).create({
            "name": "New Kodoo Account",
            "code": "9001",
            "account_type": "expense",
            "company_ids": [(4, self.company.id)],
            # No qbo_id — will be pushed
        })
        engine._push_accounts()

        engine.client.create_account.assert_called_once()
        self.assertEqual(new_acc.qbo_id, "QBO-NEW-001")

    def test_pull_account_applies_canonical_bridge_rule(self):
        self.env["qbo.account.bridge.rule"].create({
            "match_account_type": "Bank",
            "match_account_subtype": "Checking",
            "canonical_code": "110000",
            "canonical_name": "Main Operating Cash",
            "canonical_account_type": "asset_cash",
        })
        engine = self._make_engine()

        engine._upsert_accounts([
            {
                "Id": "QBO-ACC-005",
                "SyncToken": "0",
                "Name": "Checking - North Division",
                "AcctNum": "1001",
                "AccountType": "Bank",
                "AccountSubType": "Checking",
                "Active": True,
                "MetaData": {"LastUpdatedTime": "2024-01-01T00:00:00-00:00"},
            },
        ], direction="pull")

        acc = self.env["account.account"].with_company(self.company).search([
            ("qbo_id", "=", "QBO-ACC-005"),
            ("company_ids", "=", self.company.id),
        ])
        self.assertTrue(acc)
        self.assertEqual(acc.code, "110000")
        self.assertEqual(acc.name, "Main Operating Cash")
        self.assertEqual(acc.qbo_source_name, "Checking - North Division")
        self.assertEqual(acc.qbo_source_account_number, "1001")

    def test_pull_account_reuses_existing_canonical_account(self):
        self.env["qbo.account.bridge.rule"].create({
            "match_name": "Payroll Clearing",
            "canonical_code": "210500",
            "canonical_name": "Payroll Clearing",
            "canonical_account_type": "liability_current",
        })
        existing = self.env["account.account"].with_company(self.company).create({
            "name": "Payroll Clearing",
            "code": "210500",
            "account_type": "liability_current",
            "company_ids": [(4, self.company.id)],
        })
        engine = self._make_engine()

        engine._upsert_accounts([
            {
                "Id": "QBO-ACC-006",
                "SyncToken": "0",
                "Name": "Payroll Clearing",
                "AccountType": "Other Current Liability",
                "Active": True,
                "MetaData": {"LastUpdatedTime": "2024-01-01T00:00:00-00:00"},
            },
        ], direction="pull")

        updated = self.env["account.account"].with_company(self.company).search([
            ("company_ids", "=", self.company.id),
            ("code", "=", "210500"),
        ])
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated.id, existing.id)
        self.assertEqual(updated.qbo_id, "QBO-ACC-006")


class TestQBOSyncEngineProducts(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.realm = self.env["qbo.realm"].create({
            "name": "Realm B",
            "realm_id": "987654321",
            "client_id": "cid",
            "client_secret": "csec",
            "state": "connected",
        })
        self.mapping = self.env["qbo.company.mapping"].create({
            "company_id": self.company.id,
            "realm_id": self.realm.id,
            "sync_products": True,
        })

    def _make_engine(self):
        from ..services.qbo_sync_engine import QBOSyncEngine
        engine = QBOSyncEngine(self.env, self.mapping)
        engine.client = MagicMock()
        return engine

    def test_pull_product_creates_template(self):
        engine = self._make_engine()
        engine._upsert_products([
            {
                "Id": "ITEM-001",
                "SyncToken": "0",
                "Name": "Widget Pro",
                "Type": "Inventory",
                "UnitPrice": 99.99,
                "PurchaseCost": 40.0,
                "Active": True,
                "MetaData": {"LastUpdatedTime": "2024-01-01T00:00:00-00:00"},
            },
        ])
        product = self.env["product.template"].search([("qbo_id", "=", "ITEM-001")])
        self.assertTrue(product)
        self.assertAlmostEqual(product.list_price, 99.99)
