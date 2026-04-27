from odoo import Command

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSaleSubscriptionComboProduct(TestSubscriptionCommon, HttpCase):
    def test_create_invoice_with_combo_product(self):
        """ Test that a subscription with a combo product generates the correct invoice. """
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [
                Command.create({'product_id': self.product.id}),
            ],
        })
        combo_product = self._create_product(
            name="Combo product",
            type='combo',
            combo_ids=[Command.link(combo.id)],
        )

        subscription = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'user_id': self.sale_user.id,
        })
        combo_line = self.env['sale.order.line'].create({
            'order_id': subscription.id,
            'product_id': combo_product.id,
        })

        self.env['sale.order.line'].create({
            'order_id': subscription.id,
            'product_id': self.product.id,
            'combo_item_id': combo.combo_item_ids.id,
            'linked_line_id': combo_line.id,
        })
        subscription.action_confirm()

        invoice = subscription._create_recurring_invoice()
        self.assertTrue(invoice)
        self.assertEqual(len(invoice.invoice_line_ids), 2)

        self.assertEqual(invoice.invoice_line_ids[0].display_type, 'line_section')
        self.assertTrue(invoice.invoice_line_ids[0].name.startswith(combo_product.name))
        self.assertEqual(invoice.invoice_line_ids[1].display_type, 'product')
        self.assertTrue(invoice.invoice_line_ids[1].name.startswith(self.product.name))
