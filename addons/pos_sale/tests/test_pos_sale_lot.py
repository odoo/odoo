# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):
    def test_ship_later_lots(self):
        self.env.user.group_ids += self.env.ref('account.group_account_manager')
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.twenty_dollars_no_tax.product_variant_id.write({
            'tracking': 'serial',
            'is_storable': True,
            'taxes_id': []
        })
        lot_1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'company_id': self.env.company.id,
        })
        lot_2 = self.env['stock.lot'].create({
            'name': '1002',
            'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'inventory_quantity': 1,
            'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_1.id
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'inventory_quantity': 1,
            'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_2.id
        }).action_apply_inventory()

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_stva.id,
            'order_line': [(0, 0, {
                'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
                'name': self.twenty_dollars_no_tax.product_variant_id.name,
                'price_unit': self.twenty_dollars_no_tax.product_variant_id.lst_price,
                'product_uom_qty': 2,
            })],
        })
        sale_order.action_confirm()
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_stva.id,
                'shipping_date': fields.Date.today(),
            },
            'line_data': [{
                'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
                'pack_lot_ids': [[0, 0, {'lot_name': lot_1.name}]],
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            }],
            'payment_data': [
                {'payment_method_id': self.pos_config_usd.payment_method_ids[0].id}
            ]
        })
        self.assertEqual(order.picking_ids.move_line_ids.lot_id, lot_1)

    def test_read_converted_lot_quantities_pick_then_deliver(self):
        """
        Test that read_converted returns correct lot quantities with 2-step
        "Pick then Deliver" after delivery is validated (no double-counting).
        """
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )
        warehouse.delivery_steps = 'pick_ship'
        stock_location = warehouse.lot_stock_id

        product = self.env['product.product'].create({
            'name': 'Product Lot Tracked',
            'tracking': 'lot',
            'is_storable': True,
            'available_in_pos': True,
            'lst_price': 10,
        })

        lots = self.env['stock.lot'].create([
            {'name': 'LOT-1', 'product_id': product.id, 'company_id': self.env.company.id},
            {'name': 'LOT-2', 'product_id': product.id, 'company_id': self.env.company.id},
        ])
        for lot in lots:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 1,
                'location_id': stock_location.id,
                'lot_id': lot.id,
            }).action_apply_inventory()

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test'}).id,
            'warehouse_id': warehouse.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_uom_qty': 2,
                'price_unit': product.lst_price,
            })],
        })
        sale_order.action_confirm()

        pick_picking = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code != 'outgoing'
        )
        pick_picking.action_assign()
        mls = pick_picking.move_line_ids.filtered(lambda ml: ml.product_id == product)
        for ml, lot in zip(mls[:2], lots):
            ml.write({'lot_id': lot.id, 'quantity': 1})
        for ml in mls[2:]:
            ml.unlink()
        pick_picking.move_ids.picked = True
        pick_picking._action_done()

        delivery_picking = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        )
        delivery_picking.action_assign()
        delivery_picking.move_ids.picked = True
        delivery_picking._action_done()

        [conv] = sale_order.order_line.read_converted()
        self.assertEqual(conv['product_uom_qty'], 2)
        lot_qty_sum = sum(conv.get('lot_qty_by_name', {}).values())
        self.assertEqual(lot_qty_sum, 2)
