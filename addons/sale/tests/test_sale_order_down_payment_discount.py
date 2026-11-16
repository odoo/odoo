from odoo import Command
from odoo.tests import tagged

from .common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderDownPaymentDiscount(TestSaleCommon):
    """A down payment invoiced with a discount is deducted for what it charged."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'order_line': [
                # invoiced on order, so the final invoice bills it
                Command.create({
                    'product_id': cls.company_data['product_order_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 900.0,
                    'tax_id': False,
                }),
                # invoiced on delivery and nothing delivered, so it stays out of the final invoice
                Command.create({
                    'product_id': cls.company_data['product_delivery_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 3100.0,
                    'tax_id': False,
                }),
            ],
        })
        cls.sale_order.action_confirm()

    def _invoice_down_payment(self, discount):
        """Invoice a 1000 down payment, discounted on its line before being posted."""
        self.env['sale.advance.payment.inv'].with_context(
            active_model='sale.order',
            active_ids=self.sale_order.ids,
            active_id=self.sale_order.id,
        ).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 1000.0,
        }).create_invoices()
        down_payment = self.sale_order.invoice_ids.filtered(lambda move: move.state == 'draft')
        down_payment.invoice_line_ids.filtered('is_downpayment').discount = discount
        down_payment.action_post()
        return down_payment

    def _get_down_payment_line(self):
        return self.sale_order.order_line.filtered(
            lambda sol: sol.is_downpayment and not sol.display_type)

    def test_discounted_down_payment_price_unit(self):
        down_payment = self._invoice_down_payment(15.0)

        self.assertEqual(down_payment.amount_untaxed, 850.0)
        self.assertEqual(self._get_down_payment_line().price_unit, 850.0)

    def test_discounted_down_payment_final_invoice(self):
        self._invoice_down_payment(15.0)

        final_invoice = self.sale_order._create_invoices(final=True)

        self.assertEqual(final_invoice.move_type, 'out_invoice')
        self.assertEqual(final_invoice.amount_untaxed, 50.0)

    def test_down_payment_without_discount(self):
        down_payment = self._invoice_down_payment(0.0)

        self.assertEqual(down_payment.amount_untaxed, 1000.0)
        self.assertEqual(self._get_down_payment_line().price_unit, 1000.0)
