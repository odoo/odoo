# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestInvoiceDeliveryReferences(L10nInTestInvoicingCommon):

    def test_report_uses_completed_delivery_notes(self):
        self.product_a.write({'type': 'consu', 'invoice_policy': 'order'})
        order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id, 'client_order_ref': 'BUYER-PO-42',
            'order_line': [Command.create({'product_id': self.product_a.id, 'product_uom_qty': 1})],
        })
        order.action_confirm()
        invoice = order._create_invoices().with_env(self.env)
        picking = order.picking_ids
        self.assertFalse(invoice._l10n_in_get_invoice_report_header_values()['delivery_notes'])
        picking.move_ids.write({'quantity': 1, 'picked': True})
        picking.button_validate()
        self.assertEqual(picking.state, 'done')
        values = invoice._l10n_in_get_invoice_report_header_values()
        self.assertEqual(values['delivery_notes'], [picking.name])
        self.assertEqual(values['delivery_note_dates'], [fields.Date.to_date(picking.date_done)])
        self.assertEqual(values['buyer_order_no'], 'BUYER-PO-42')
