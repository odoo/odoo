from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInvoiceLineClassification(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "Invoiced client"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Sold service",
                "type": "service",
                "invoice_policy": "ordered",
                "list_price": 1000.0,
            }
        )

    def _confirmed_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        return order

    def _downpayment_invoice(self, order, amount=300.0):
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_model="sale.order", active_ids=order.ids)
            .create({"advance_payment_method": "fixed", "fixed_amount": amount})
        )
        wizard.create_invoices()
        return order.invoice_ids[-1]

    def test_advance_invoice_is_recognised_as_a_down_payment(self):
        order = self._confirmed_order()
        invoice = self._downpayment_invoice(order)
        self.assertTrue(invoice._is_downpayment())

    def test_ordinary_invoice_is_not_a_down_payment(self):
        order = self._confirmed_order()
        invoice = order._create_invoices()
        self.assertFalse(invoice._is_downpayment())

    def test_invoice_without_a_sale_order_is_not_a_down_payment(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_line_ids": [
                    Command.create({"product_id": self.product.id, "quantity": 1})
                ],
            }
        )
        self.assertFalse(invoice._is_downpayment())

    def test_final_invoice_points_back_to_its_down_payment_lines(self):
        order = self._confirmed_order()
        self._downpayment_invoice(order)
        final = order._create_invoices(final=True)
        downpayment_lines = final.invoice_line_ids._get_downpayment_lines()
        self.assertTrue(downpayment_lines)
        self.assertTrue(
            all(line.move_id._is_downpayment() for line in downpayment_lines)
        )

    def test_ordinary_invoice_has_no_down_payment_lines(self):
        order = self._confirmed_order()
        invoice = order._create_invoices()
        self.assertFalse(invoice.invoice_line_ids._get_downpayment_lines())

    def test_sale_lines_are_linked_when_copying_business_fields(self):
        fields_kept = self.env["account.move.line"]._get_fields_order_line_link()
        self.assertIn("sale_line_ids", fields_kept)

    def test_company_discount_product_marks_a_line_as_a_discount(self):
        discount_product = self.env["product.product"].create(
            {"name": "Discount", "type": "service"}
        )
        self.env.company.sudo().sale_config_id.sale_discount_product_id = (
            discount_product
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_line_ids": [
                    Command.create({"product_id": discount_product.id, "quantity": 1}),
                    Command.create({"product_id": self.product.id, "quantity": 1}),
                ],
            }
        )
        discount_lines = invoice.invoice_line_ids._filtered_discount_lines()
        self.assertEqual(discount_lines.product_id, discount_product)

    def test_other_products_are_not_discounts(self):
        self.env.company.sudo().sale_config_id.sale_discount_product_id = False
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_line_ids": [
                    Command.create({"product_id": self.product.id, "quantity": 1})
                ],
            }
        )
        self.assertFalse(invoice.invoice_line_ids._filtered_discount_lines())
