# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import Command

from odoo.addons.point_of_sale.tests.test_point_of_sale_flow import TestPointOfSaleFlow


@odoo.tests.tagged('post_install', '-at_install')
class TestPosPickingBackorder(TestPointOfSaleFlow):

    def test_pos_backorder_picking_shares_pos_order_origin(self):
        """Mixed order: untracked line with stock + serial line without stock nor SN."""
        qty_product = self.env['product.product'].create({
            'name': 'POS Qty Product Backorder Test',
            'is_storable': True,
            'tracking': 'none',
            'available_in_pos': True,
        })
        serial_product = self.env['product.product'].create({
            'name': 'POS Serial Product Backorder Test',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })
        wh_location = self.company_data['default_warehouse'].lot_stock_id
        shelf_location = self.env['stock.location'].create({
            'name': 'pos_backorder_test_shelf',
            'usage': 'internal',
            'location_id': wh_location.id,
        })
        self.env['stock.quant']._update_available_quantity(qty_product, shelf_location, 5)

        self.pos_config_usd.open_ui()

        untax_qty, atax_qty = self.compute_tax(qty_product, 10.0, 1)
        untax_ser, atax_ser = self.compute_tax(serial_product, 20.0, 1)
        total = untax_qty + atax_qty + untax_ser + atax_ser

        pos_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.pos_config_usd.current_session_id.id,
            'pricelist_id': self.partner_manv.property_product_pricelist.id,
            'partner_id': self.partner_manv.id,
            'lines': [Command.create({
                'name': "OL/QTY",
                'product_id': qty_product.id,
                'price_unit': 10.0,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': [Command.set(qty_product.taxes_id.filtered(lambda t: t.company_id.id == self.env.company.id).ids)],
                'price_subtotal': untax_qty,
                'price_subtotal_incl': untax_qty + atax_qty,
                'pack_lot_ids': [],
            }), Command.create({
                'name': "OL/SERIAL",
                'product_id': serial_product.id,
                'price_unit': 20.0,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': [Command.set(serial_product.taxes_id.filtered(lambda t: t.company_id.id == self.env.company.id).ids)],
                'price_subtotal': untax_ser,
                'price_subtotal_incl': untax_ser + atax_ser,
                'pack_lot_ids': [],
            })],
            'amount_tax': atax_qty + atax_ser,
            'amount_total': total,
            'amount_paid': 0,
            'amount_return': 0,
            'last_order_preparation_change': '{}',
        })

        payment_ctx = {'active_ids': [pos_order.id], 'active_id': pos_order.id}
        self.env['pos.make.payment'].with_context(payment_ctx).create({
            'amount': total,
        }).with_context({'active_id': pos_order.id}).check()

        self.assertEqual(pos_order.state, 'paid')
        pickings = pos_order.picking_ids
        self.assertGreaterEqual(
            len(pickings),
            2,
            "A done delivery and a backorder picking are expected when the serial line cannot be fulfilled.",
        )

        for picking in pickings:
            self.assertEqual(
                picking.origin,
                pos_order.name,
                "All POS-related pickings (including backorders) must show the POS order as Source Document.",
            )
            self.assertEqual(picking.pos_order_id, pos_order)
            self.assertEqual(picking.pos_session_id, pos_order.session_id)
