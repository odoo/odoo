# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tests import common
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestUpdateQuantity(common.TransactionCase):

    def setUp(self):
        super(TestUpdateQuantity, self).setUp()

        self.PurchaseOrder = self.env['purchase.order']
        self.SaleOrder = self.env['sale.order']
        self.MrpBom = self.env['mrp.bom']
        self.Product = self.env['product.product']
        self.ProcurementOrder = self.env['procurement.order']

        self.route_mto = self.env.ref('stock.warehouse0').mto_pull_id.route_id.id
        self.route_buy = self.env.ref('stock.warehouse0').buy_pull_id.route_id.id

        self.computer_kit = self.Product.create({
            'name': 'Computer Kit',
            'type': 'product',
            'route_ids': [(6, 0, [self.route_buy, self.route_mto])],
            'seller_ids': [(0, 0, {'name': self.env.ref('base.res_partner_2').id})],
            })

        self.mouse = self.Product.create({'name': 'Optical Mouse'})
        self.keyboard = self.Product.create({'name': 'Apple Keyboard'})

        # Create BOM of product computer kit.
        self.product_bom = self.MrpBom.create({
            'product_id': self.computer_kit.id,
            'product_tmpl_id': self.computer_kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                    (0, 0, {
                        'product_id': self.mouse.id,
                        'product_qty': 2,
                        }),
                    (0, 0, {
                        'product_id': self.keyboard.id,
                        'product_qty': 1,
                        })],
        })

        # Create purchase order with one purchase order line containing product of computer kit.
        self.po_vals = {
            'partner_id': self.env.ref('base.res_partner_1').id,
            'order_line': [
                (0, 0, {
                    'name': self.computer_kit.name,
                    'product_id': self.computer_kit.id,
                    'product_qty': 3.0,
                    'product_uom': self.computer_kit.uom_id.id,
                    'price_unit': 500.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        }

        self.procurement_vals = {
            'name': self.computer_kit.name,
            'product_id': self.computer_kit.id,
            'product_qty': 10,
            'product_uom': self.env.ref('product.product_uom_unit').id,
            'warehouse_id': self.env.ref('stock.warehouse0').id,
            'location_id': self.env.ref('stock.warehouse0').lot_stock_id.id,
            'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }

    def test_00_update_qty_kit(self):
        """Check move creation when update quantity in purchase line of phantom product ."""

        # Draft Purchase Order created
        PackOperation = self.env['stock.pack.operation']
        self.po = self.PurchaseOrder.create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: purchase order not created')

        # Purchase Order confirm
        self.po.button_confirm()
        # Check purchase order status after confirm.
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "purchase"')
        # Check picking related to purchase order.
        pick = self.po.picking_ids
        self.assertEqual(len(pick), 1, 'Purchase: One Picking should be created')

        move_mouse = pick.move_lines.filtered(lambda x: x.product_id == self.mouse)
        move_keyboard = pick.move_lines.filtered(lambda x: x.product_id == self.keyboard)
        # Check move of mouse and keyboard.
        self.assertEqual(len(move_mouse), 1, 'Purchase: Wrong move created for component mouse')
        self.assertEqual(len(move_keyboard), 1, 'Purchase: Wrong move created for component keyboard')

        # Check quantity of mouse and keyboard move ( it should be created based on bom )
        # (po line quantity) * ( bom line quantity) = (3 * 2) = 6
        self.assertEqual(move_mouse.product_qty, 6, 'Purchase: Wrong quantity on move for component mouse')
        # (po line quantity) * ( bom line quantity) = (3 * 1) = 7
        self.assertEqual(move_keyboard.product_qty, 3, 'Purchase: Wrong quantity on move for component keyboard')
        # Transfer picking
        pick.force_assign()
        pick.do_prepare_partial()
        pack_opt_mouse = PackOperation.search([('product_id', '=', self.mouse.id), ('picking_id', '=', pick.id)], limit=1)
        pack_opt_mouse.write({'product_qty': 4})
        pack_opt_keybord = PackOperation.search([('product_id', '=', self.keyboard.id), ('picking_id', '=', pick.id)], limit=1)
        pack_opt_keybord.write({'product_qty': 2})
        pick.do_transfer()
        # Check Receive quantity of product in purchase order line
        self.assertEqual(self.po.order_line.qty_received, 2, "Purchase : Received quantity should be 2.0 after transfer")

        # -----------------------------------------------
        # Update quantity of product in Purchase Order.
        # -----------------------------------------------
        # Change computer kit quantity 3 to 7

        with self.assertRaises(UserError):
            self.po.order_line.write({'product_qty': 7})
