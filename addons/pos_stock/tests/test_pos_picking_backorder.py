# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.pos_stock.tests.common import CommonPosStockTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPosPickingBackorder(CommonPosStockTest):

    def test_pos_backorder_picking_shares_pos_order_origin(self):
        """Mixed order: untracked line with stock + serial line without stock nor SN."""
        qty_product = self.env['product.product'].create({
            'name': 'POS Qty Product Backorder Test',
            'store_by': 'quantity',
            'available_in_pos': True,
            'list_price': 10.0,
        })
        serial_product = self.env['product.product'].create({
            'name': 'POS Serial Product Backorder Test',
            'store_by': 'serial',
            'available_in_pos': True,
            'list_price': 20.0,
        })
        wh_location = self.company_data['default_warehouse'].lot_stock_id
        shelf_location = self.env['stock.location'].create({
            'name': 'pos_backorder_test_shelf',
            'usage': 'internal',
            'location_id': wh_location.id,
        })
        self.env['stock.quant']._update_available_quantity(qty_product, shelf_location, 5)

        self.pos_config_usd.open_ui()
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_manv.id,
                'pricelist_id': self.partner_manv.property_product_pricelist.id,
            },
            'line_data': [
                {'product_id': qty_product.id},
                {'product_id': serial_product.id},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id},
            ],
        })

        self.assertEqual(order.state, 'paid')
        pickings = order.picking_ids
        self.assertGreaterEqual(
            len(pickings),
            2,
            "A done delivery and a backorder picking are expected when the serial line cannot be fulfilled.",
        )

        for picking in pickings:
            self.assertEqual(
                picking.origin,
                order.name,
                "All POS-related pickings (including backorders) must show the POS order as Source Document.",
            )
            self.assertEqual(picking.pos_order_id, order)
            self.assertEqual(picking.pos_session_id, order.session_id)
