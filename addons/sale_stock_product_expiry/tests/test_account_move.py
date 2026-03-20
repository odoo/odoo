# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.addons.sale_stock.tests.common import TestSaleStockCommon


class TestInvoicedLotValues(TestSaleStockCommon):
    def test_lot_expiration(self):
        """ Checks if lot expiration date is included in `_get_invoiced_lot_values()` """
        expiration_date = fields.Datetime.today() + relativedelta(days=3)
        lot = self.env['stock.lot'].create({
            'name': 'lot_product_a_0001',
            'product_id': self.product_a.id,
            'expiration_date': fields.Datetime.to_string(expiration_date),
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                })
            ]
        })
        # Set lots, validate records, generate invoices (required for `_get_invoiced_lot_values()`)
        sale_order.action_confirm()
        sale_order.picking_ids.move_line_ids.lot_id = lot
        sale_order.picking_ids.button_validate()
        sale_order._create_invoices()
        invoice = sale_order.invoice_ids
        invoice.action_post()
        lot_values = invoice._get_invoiced_lot_values()

        self.assertEqual(len(lot_values), 1)
        self.assertEqual(lot_values[0]['lot_expiration_date'], expiration_date)
