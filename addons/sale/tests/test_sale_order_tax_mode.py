from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.test_account_move_tax_mode import TestDocumentTaxModeCommon


@tagged('post_install', '-at_install')
class TestSaleOrderTaxMode(TestDocumentTaxModeCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')
        cls.sale_order_one_line_with_product = cls._create_sale_order_one_line(
            product_id=cls.test_product_a,
            company_id=cls.env.company.id,
            confirm=False,
        )

    def test_sale_order_tax_mode_change_with_product(self):
        sale_order = self.sale_order_one_line_with_product
        self._test_tax_mode_change_with_product(sale_order, 'sale_order')

    def test_sale_order_tax_mode_change_with_product_with_tax_override_taxes_company_tax_excluded(self):
        sale_order = self.sale_order_one_line_with_product
        self._test_tax_mode_change_with_product_with_tax_override_taxes_company_tax_excluded(sale_order, 'sale_order')

    def test_sale_order_tax_mode_change_with_product_with_tax_override_taxes_company_tax_included(self):
        self.env.company.account_price_include = 'tax_included'
        sale_order = self._create_sale_order_one_line(
            product_id=self.test_product_b,
            confirm=False,
        )
        self._test_tax_mode_change_with_product_with_tax_override_taxes_company_tax_included(sale_order, 'sale_order')

    def test_sale_order_tax_mode_change_with_product_with_mixed_taxes_company_tax_excluded(self):
        sale_order = self.sale_order_one_line_with_product
        self._test_tax_mode_change_with_product_with_mixed_taxes_company_tax_excluded(sale_order, 'sale_order')

    def test_sale_order_tax_mode_change_with_product_with_mixed_taxes_company_tax_included(self):
        self.env.company.account_price_include = 'tax_included'
        sale_order = self._create_sale_order_one_line(
            product_id=self.test_product_b,
            confirm=False,
        )
        self._test_tax_mode_change_with_product_with_mixed_taxes_company_tax_included(sale_order, 'sale_order')

    def test_sale_order_tax_mode_change_manual_price_unit_with_product(self):
        sale_order = self.sale_order_one_line_with_product
        self._test_tax_mode_change_manual_price_unit_with_product(sale_order, 'sale_order')

    def test_sale_order_tax_mode_change_add_tax_manual_price_unit_with_product(self):
        sale_order = self.sale_order_one_line_with_product
        self._test_tax_mode_change_add_tax_manual_price_unit_with_product(sale_order, 'sale_order')

    def test_sale_order_tax_mode_change_keeps_combo_item_price_unit_unchanged(self):
        """A combo item line's price should be unaffected by a document tax mode
        switch, the same way a regular product line's price is."""
        combo = self.env["product.combo"].create({
            "name": "Test Combo",
            "company_id": self.env.company.id,
            "combo_item_ids": [Command.create({"product_id": self.test_product_a.id})],
        })
        combo_product = self.env["product.product"].create({
            "name": "Test Combo Product",
            "type": "combo",
            "list_price": 60.0,
            "combo_ids": [Command.set([combo.id])],
            "company_id": self.env.company.id,
        })

        order = self.env["sale.order"].create({"partner_id": self.partner_a.id})
        combo_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": combo_product.id,
        })
        combo_item_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.test_product_a.id,
            "combo_item_id": combo.combo_item_ids.id,
            "linked_line_id": combo_line.id,
        })

        self.assertEqual(order.document_tax_mode, "tax_excluded")
        self.assertEqual(combo_item_line.price_unit, 60.0)
        self.assertRecordValues(combo_item_line, [{"price_subtotal": 60.0, "price_total": 66.0}])

        with Form(order) as order_form:
            order_form.document_tax_mode = "tax_included"

        self.assertEqual(combo_item_line.price_unit, 60.0)
        self.assertRecordValues(combo_item_line, [{"price_subtotal": 54.55, "price_total": 60.0}])

    def test_invoice_grouping_different_tax_modes(self):
        order1 = self._create_sale_order_one_line(
            product_id=self.test_product_a,
            company_id=self.env.company.id,
            confirm=False,
            document_tax_mode="tax_excluded",
        )
        order1.action_confirm()
        order2 = self._create_sale_order_one_line(
            product_id=self.test_product_a,
            company_id=self.env.company.id,
            confirm=False,
            document_tax_mode="tax_included",
        )
        order2.action_confirm()

        invoices = (order1 + order2)._create_invoices()
        self.assertEqual(len(invoices), 2)
        invoice1 = invoices.filtered(lambda m: order1 in m.line_ids.sale_line_ids.order_id)
        invoice2 = invoices.filtered(lambda m: order2 in m.line_ids.sale_line_ids.order_id)
        self.assertRecordValues(
            invoice1, [{"document_tax_mode": "tax_excluded", "amount_total": order1.amount_total}]
        )
        self.assertRecordValues(
            invoice2, [{"document_tax_mode": "tax_included", "amount_total": order2.amount_total}]
        )

    def test_invoice_grouping_same_tax_mode(self):
        order1 = self._create_sale_order_one_line(
            product_id=self.test_product_a,
            company_id=self.env.company.id,
            confirm=False,
            document_tax_mode="tax_excluded",
        )
        order1.action_confirm()
        order2 = self._create_sale_order_one_line(
            product_id=self.test_product_a,
            company_id=self.env.company.id,
            confirm=False,
            document_tax_mode="tax_excluded",
        )
        order2.action_confirm()

        invoice = (order1 + order2)._create_invoices()
        self.assertEqual(len(invoice), 1)
        self.assertRecordValues(
            invoice,
            [
                {
                    "document_tax_mode": "tax_excluded",
                    "amount_total": order1.amount_total + order2.amount_total,
                }
            ],
        )
