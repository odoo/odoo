# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import exceptions
from odoo.tests import Form, TransactionCase


class TestSaleCommissionSalesman(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Test Product 1", "list_price": 100}
        )
        SaleCommission = cls.env["commission"]
        cls.commission_1 = SaleCommission.create(
            {"name": "1% commission", "fix_qty": 1.0}
        )
        Partner = cls.env["res.partner"]
        cls.salesman = cls.env["res.users"].create(
            {"name": "Test agent", "login": "sale_comission_salesman_test"}
        )
        cls.agent = cls.salesman.partner_id
        cls.agent.write(
            {
                "agent": True,
                "salesman_as_agent": True,
                "commission_id": cls.commission_1.id,
            }
        )
        cls.other_agent = Partner.create(
            {
                "name": "Test other agent",
                "agent": True,
                "commission_id": cls.commission_1.id,
            }
        )
        cls.partner = Partner.create({"name": "Partner test"})
        cls.sale_order = cls.env["sale.order"].create(
            {"partner_id": cls.partner.id, "user_id": cls.salesman.id}
        )
        cls.invoice = cls.env["account.move"].create(
            {
                "partner_id": cls.partner.id,
                "invoice_user_id": cls.salesman.id,
                "move_type": "out_invoice",
            }
        )

    def test_check_salesman_commission(self):
        with self.assertRaises(exceptions.ValidationError):
            self.agent.commission_id = False

    def test_sale_commission_salesman(self):
        line = self.env["sale.order.line"].create(
            {"order_id": self.sale_order.id, "product_id": self.product.id}
        )
        self.assertTrue(line.agent_ids)
        self.assertTrue(line.agent_ids.agent_id, self.agent)
        self.assertTrue(line.agent_ids.commission_id, self.commission_1)

    def test_sale_commission_salesman_no_population(self):
        self.partner.agent_ids = [(4, self.other_agent.id)]
        line = self.env["sale.order.line"].create(
            {"order_id": self.sale_order.id, "product_id": self.product.id}
        )
        self.assertTrue(len(line.agent_ids), 1)
        self.assertTrue(line.agent_ids.agent_id, self.other_agent)

    def test_invoice_commission_salesman(self):
        invoice_form = Form(self.invoice)
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product
        invoice_form.save()
        line = self.invoice.invoice_line_ids
        self.assertTrue(line.agent_ids)
        self.assertTrue(line.agent_ids.agent_id, self.agent)
        self.assertTrue(line.agent_ids.commission_id, self.commission_1)

    def test_invoice_commission_salesman_no_population(self):
        self.partner.agent_ids = [(4, self.other_agent.id)]
        invoice_form = Form(self.invoice)
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product
        invoice_form.save()
        line = self.invoice.invoice_line_ids
        self.assertTrue(line.agent_ids)
        self.assertTrue(line.agent_ids.agent_id, self.other_agent)
