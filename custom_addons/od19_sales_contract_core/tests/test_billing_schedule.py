from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestContractBillingSchedule(TransactionCase):
    """Tests for the contract billing schedule (installments)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contractor = cls.env["res.partner"].create({"name": "Contractor BS"})
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "Owner BS",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Schedule Project", "project_owner_id": cls.owner.id}
        )

    def _make_contract(self, limit=3000.0):
        return self.env["od19.sales.contract"].create(
            {
                "name": "MC-BS-0001",
                "partner_id": self.contractor.id,
                "od19_project_id": self.project.id,
                "limit_amount": limit,
                "over_limit_policy": "block",
            }
        )

    def _make_line(self, contract, name, sequence, percent):
        return self.env["od19.contract.billing.line"].create(
            {
                "name": name,
                "contract_id": contract.id,
                "sequence": sequence,
                "line_type": "percent",
                "percent": percent,
            }
        )

    def test_percent_amount_is_derived_from_limit(self):
        contract = self._make_contract(limit=3000.0)
        self._make_line(contract, "Installment 1", 1, 30.0)
        self._make_line(contract, "Installment 2", 2, 40.0)
        self._make_line(contract, "Installment 3", 3, 30.0)
        amounts = contract.billing_line_ids.sorted("sequence").mapped("amount")
        self.assertEqual(amounts, [900.0, 1200.0, 900.0])

    def test_billing_totals_are_computed(self):
        contract = self._make_contract(limit=3000.0)
        line1 = self._make_line(contract, "Installment 1", 1, 30.0)
        self._make_line(contract, "Installment 2", 2, 40.0)
        contract.invalidate_recordset()
        self.assertEqual(contract.billing_scheduled_amount, 2100.0)
        self.assertEqual(contract.billing_invoiced_amount, 0.0)
        self.assertEqual(contract.billing_remaining_amount, 2100.0)
        # Mark the first installment as invoiced
        line1.state = "invoiced"
        contract.invalidate_recordset()
        self.assertEqual(contract.billing_invoiced_amount, 900.0)
        self.assertEqual(contract.billing_remaining_amount, 1200.0)

    def test_total_billing_cannot_exceed_limit(self):
        contract = self._make_contract(limit=1000.0)
        self._make_line(contract, "Installment 1", 1, 60.0)
        with self.assertRaises(ValidationError):
            self._make_line(contract, "Installment 2", 2, 60.0)

    def test_create_invoice_blocked_when_earlier_installment_open(self):
        contract = self._make_contract(limit=3000.0)
        self._make_line(contract, "Installment 1", 1, 30.0)
        line2 = self._make_line(contract, "Installment 2", 2, 40.0)
        with self.assertRaises(UserError):
            line2.action_create_invoice()

    def test_create_invoice_requires_sale_order(self):
        contract = self._make_contract(limit=3000.0)
        line = self._make_line(contract, "Installment 1", 1, 30.0)
        with self.assertRaises(UserError):
            line.action_create_invoice()

    def test_create_invoice_blocked_when_already_invoiced(self):
        contract = self._make_contract(limit=3000.0)
        line = self._make_line(contract, "Installment 1", 1, 30.0)
        line.state = "invoiced"
        with self.assertRaises(UserError):
            line.action_create_invoice()
