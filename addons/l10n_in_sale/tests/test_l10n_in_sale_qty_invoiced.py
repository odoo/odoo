from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSaleQtyInvoiced(L10nInTestInvoicingCommon):
    _test_user_groups = None  # FIXME list needed groups

    def _get_confirmed_invoiced_order(self):
        order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_a.id, 'product_uom_qty': 10})],
        })
        order.action_confirm()
        order._create_invoices().action_post()
        return order

    def test_qty_invoiced_standard_credit_note(self):
        order = self._get_confirmed_invoiced_order()
        self._create_credit_note(inv=order.invoice_ids)
        self.assertEqual(
            order.order_line.qty_invoiced, 0.0, "A standard credit note should reduce the invoiced quantity"
        )

    def test_qty_invoiced_price_adjustment_credit_note(self):
        order = self._get_confirmed_invoiced_order()
        credit_note = self._create_credit_note(inv=order.invoice_ids, post=False)
        credit_note.l10n_in_adjustment_type = 'price_adjustment'
        credit_note.action_post()
        self.assertEqual(
            order.order_line.qty_invoiced, 10.0, "A price adjustment credit note must not reduce the invoiced quantity"
        )
