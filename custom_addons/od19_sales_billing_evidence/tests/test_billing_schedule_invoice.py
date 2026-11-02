from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestBillingScheduleInvoice(TransactionCase):
    """Tests issue of installment invoices through the billing evidence gate."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contractor = cls.env["res.partner"].create({"name": "Contractor BI"})
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "Owner BI",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Installment Project", "project_owner_id": cls.owner.id}
        )
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Customer BI",
                "is_company": True,
                "od19_is_commercial_customer": True,
                "email": "customer-bi@example.com",
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Service BI", "type": "service", "list_price": 900.0}
        )
        cls.evidence_type = cls.env["od19.billing.evidence.type"].create(
            {
                "name": "Delivery Note BI",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )

    def _make_contract(self, limit=3000.0):
        return self.env["od19.sales.contract"].create(
            {
                "name": "MC-BI-0001",
                "partner_id": self.contractor.id,
                "od19_project_id": self.project.id,
                "limit_amount": limit,
                "over_limit_policy": "warn",
            }
        )

    def _make_order(self, contract):
        return self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
                "od19_contract_id": contract.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                        },
                    )
                ],
            }
        )

    def _make_line(self, contract, order, name, sequence, percent):
        return self.env["od19.contract.billing.line"].create(
            {
                "name": name,
                "contract_id": contract.id,
                "sequence": sequence,
                "line_type": "percent",
                "percent": percent,
                "sale_order_id": order.id,
            }
        )

    def _verify_evidence(self, order):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "evidence.pdf",
                "datas": "bW9ja2RhdGE=",
                "res_model": "od19.billing.evidence",
            }
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "DN-BI-001",
                "sale_order_id": order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        order._compute_od19_billing_readiness_state()

    def test_installment_invoice_blocked_without_verified_evidence(self):
        contract = self._make_contract()
        order = self._make_order(contract)
        order.action_confirm()
        order._compute_od19_billing_readiness_state()
        line = self._make_line(contract, order, "Installment 1", 1, 30.0)
        with self.assertRaises(UserError):
            line.action_create_invoice()
        self.assertEqual(line.state, "draft")

    def test_installment_invoice_created_when_evidence_verified(self):
        contract = self._make_contract()
        order = self._make_order(contract)
        order.action_confirm()
        self._verify_evidence(order)
        line = self._make_line(contract, order, "Installment 1", 1, 30.0)
        line.action_create_invoice()
        self.assertEqual(line.state, "invoiced")
        self.assertTrue(line.invoice_id)
        self.assertEqual(line.invoice_id.move_type, "out_invoice")

    def test_contract_next_installment_invoice_uses_first_open_line(self):
        contract = self._make_contract()
        order1 = self._make_order(contract)
        order1.action_confirm()
        self._verify_evidence(order1)
        order2 = self._make_order(contract)
        order2.action_confirm()
        self._verify_evidence(order2)
        line1 = self._make_line(contract, order1, "Installment 1", 1, 30.0)
        self._make_line(contract, order2, "Installment 2", 2, 40.0)
        contract.action_create_next_billing_invoice()
        self.assertEqual(line1.state, "invoiced")
