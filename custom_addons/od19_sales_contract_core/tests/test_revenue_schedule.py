from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestContractRevenueSchedule(TransactionCase):
    """Tests for the TFRS 15 revenue recognition schedule."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contractor = cls.env["res.partner"].create({"name": "Contractor RS"})
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "Owner RS",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Revenue Project", "project_owner_id": cls.owner.id}
        )
        cls.deferred_account = cls.env["account.account"].create(
            {
                "name": "Deferred Revenue",
                "code": "214200",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        cls.revenue_account = cls.env["account.account"].create(
            {
                "name": "Contract Revenue",
                "code": "411000",
                "account_type": "income",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Revenue Journal",
                "type": "general",
                "code": "OREV",
                "default_account_id": cls.deferred_account.id,
            }
        )

    def _make_contract(self, limit=3000.0, **kwargs):
        vals = {
            "name": "MC-RS-0001",
            "partner_id": self.contractor.id,
            "od19_project_id": self.project.id,
            "limit_amount": limit,
            "over_limit_policy": "block",
            "revenue_journal_id": self.journal.id,
            "deferred_revenue_account_id": self.deferred_account.id,
            "revenue_account_id": self.revenue_account.id,
        }
        vals.update(kwargs)
        return self.env["od19.sales.contract"].create(vals)

    def _make_line(
        self, contract, name, sequence, percent, method="percent", progress=0.0
    ):
        return self.env["od19.contract.revenue.line"].create(
            {
                "name": name,
                "contract_id": contract.id,
                "sequence": sequence,
                "recognition_method": method,
                "percent": percent,
                "progress_percent": progress,
            }
        )

    def _gl_credit(self, move, account):
        return sum(
            move.line_ids.filtered(
                lambda line: line.account_id == account
            ).mapped("credit")
        )

    def test_percent_derives_allocated_amount(self):
        contract = self._make_contract(limit=3000.0)
        self._make_line(contract, "PO 1", 1, 30.0)
        self._make_line(contract, "PO 2", 2, 40.0)
        self._make_line(contract, "PO 3", 3, 30.0)

        amounts = contract.revenue_line_ids.sorted("sequence").mapped("total_amount")
        self.assertEqual(amounts, [900.0, 1200.0, 900.0])
        self.assertEqual(contract.revenue_total_amount, 3000.0)
        self.assertEqual(contract.revenue_recognized_amount, 0.0)
        self.assertEqual(contract.revenue_deferred_amount, 3000.0)

    def test_recognition_posts_entry_and_reconciles_with_gl(self):
        contract = self._make_contract(limit=3000.0)
        line = self._make_line(contract, "PO 1", 1, 30.0)
        self._make_line(contract, "PO 2", 2, 40.0)
        self._make_line(contract, "PO 3", 3, 30.0)

        line.action_recognize()
        line.invalidate_recordset()
        contract.invalidate_recordset()

        self.assertEqual(len(line.move_ids), 1)
        move = line.move_ids
        self.assertEqual(move.state, "posted")
        self.assertEqual(
            move.line_ids.filtered(
                lambda ml: ml.account_id == self.deferred_account
            ).debit,
            900.0,
        )
        # The recognized amount is exactly what landed in the revenue account.
        self.assertEqual(self._gl_credit(move, self.revenue_account), 900.0)
        self.assertEqual(line.recognized_amount, 900.0)
        self.assertEqual(line.remaining_amount, 0.0)
        self.assertEqual(line.state, "recognized")
        self.assertEqual(contract.revenue_recognized_amount, 900.0)
        self.assertEqual(contract.revenue_deferred_amount, 2100.0)

    def test_progress_method_recognizes_partial_amount(self):
        contract = self._make_contract(limit=1000.0)
        line = self._make_line(
            contract, "PO progress", 1, 100.0, method="progress", progress=40.0
        )

        line.action_recognize()
        line.invalidate_recordset()
        self.assertEqual(line.recognized_amount, 400.0)
        self.assertEqual(line.state, "partial")

        line.progress_percent = 100.0
        line.action_recognize()
        line.invalidate_recordset()
        self.assertEqual(line.recognized_amount, 1000.0)
        self.assertEqual(line.state, "recognized")
        self.assertEqual(len(line.move_ids), 2)

    def test_recognize_requires_contract_accounts(self):
        contract = self.env["od19.sales.contract"].create(
            {
                "name": "MC-RS-NOACC",
                "partner_id": self.contractor.id,
                "od19_project_id": self.project.id,
                "limit_amount": 1000.0,
            }
        )
        line = self._make_line(contract, "PO 1", 1, 100.0)
        with self.assertRaises(UserError):
            line.action_recognize()

    def test_cannot_recognize_beyond_allocation(self):
        contract = self._make_contract(limit=3000.0)
        line = self._make_line(contract, "PO 1", 1, 30.0)
        line.action_recognize()
        with self.assertRaises(UserError):
            line.action_recognize()

    def test_contract_bulk_recognize_all_obligations(self):
        contract = self._make_contract(limit=3000.0)
        self._make_line(contract, "PO 1", 1, 30.0)
        self._make_line(contract, "PO 2", 2, 40.0)
        self._make_line(contract, "PO 3", 3, 30.0)

        contract.action_recognize_revenue()
        contract.invalidate_recordset()

        self.assertEqual(contract.revenue_recognized_amount, 3000.0)
        self.assertEqual(contract.revenue_deferred_amount, 0.0)
        self.assertEqual(len(contract.revenue_line_ids.move_ids), 3)
        self.assertEqual(
            set(contract.revenue_line_ids.mapped("state")), {"recognized"}
        )

    def test_total_allocation_cannot_exceed_limit(self):
        contract = self._make_contract(limit=1000.0)
        self._make_line(contract, "PO 1", 1, 60.0)
        with self.assertRaises(ValidationError):
            self._make_line(contract, "PO 2", 2, 60.0)

    def test_progress_percent_range_is_enforced(self):
        contract = self._make_contract(limit=1000.0)
        with self.assertRaises(ValidationError):
            self._make_line(
                contract, "PO bad", 1, 100.0, method="progress", progress=150.0
            )
