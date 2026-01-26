# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon
from odoo.tests import tagged
from odoo import Command


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPurchaseRequisitionStock(TestPurchaseRequisitionCommon):

    def test_02_purchase_requisition_stock(self):
        """Plays with the sequence of regular supplier infos and one created by blanket orders."""
        # Product creation
        unit = self.ref("uom.product_uom_unit")
        warehouse1 = self.env.ref('stock.warehouse0')
        route_buy = self.ref('purchase_stock.route_warehouse0_buy')
        route_mto = warehouse1.mto_pull_id.route_id.id
        vendor1 = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'BBB', 'email': 'from.test2@example.com'})
        product_test = self.env['product.product'].create({
            'name': 'Usb Keyboard',
            'is_storable': True,
            'uom_id': unit,
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })
        supplier_info1 = self.env['product.supplierinfo'].create({
            'product_id': product_test.id,
            'partner_id': vendor1.id,
            'price': 50,
        })

        # Stock picking
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        move1 = self.env['stock.move'].create({
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'uom_id': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()

        # Verification : there should be a purchase order created with the good price
        purchase1 = self.env['purchase.order'].search([('partner_id', '=', vendor1.id)])
        self.assertEqual(purchase1.order_line.price_unit, 50, 'The price on the purchase order is not the supplierinfo one')

        # Blanket order creation
        line1 = (0, 0, {'product_id': product_test.id, 'product_qty': 18, 'uom_id': product_test.uom_id.id, 'price_unit': 50})
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'requisition_type': 'blanket_order',
            'vendor_id': vendor2.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_blanket.action_confirm()

        # Second stock move
        move2 = self.env['stock.move'].create({
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'uom_id': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10
        })
        move2._action_confirm()

        # As the supplier.info linked to the blanket order has the same price, the first one is stille used.
        self.assertEqual(purchase1.order_line.product_qty, 20)

        # Update the sequence of the blanket order's supplier info.
        supplier_info1.sequence = 2
        requisition_blanket.line_ids.supplier_info_ids.sequence = 1
        # In [13]: [(x.sequence, x.min_qty, x.price, x.partner_id.name) for x in supplier_info1 + requisition_blanket.line_ids.supplier_info_ids]
        # Out[13]: [(2, 0.0, 50.0, 'AAA'), (1, 0.0, 50.0, 'BBB')]

        # Second stock move
        move3 = self.env['stock.move'].create({
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'uom_id': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10
        })
        move3._action_confirm()

        # Verifications
        purchase2 = self.env['purchase.order'].search([('partner_id', '=', vendor2.id), ('requisition_id', '=', requisition_blanket.id)])
        self.assertEqual(len(purchase2), 1)
        self.assertEqual(purchase2.order_line.price_unit, 50, 'The price on the purchase order is not the blanquet order one')

    def test_03_purchase_requisition_stock(self):
        """ Two blanket orders on different 'make to order' products must generate
        two different purchase orders
        """

        # Product creation
        unit = self.ref("uom.product_uom_unit")
        warehouse1 = self.env.ref('stock.warehouse0')
        route_buy = self.ref('purchase_stock.route_warehouse0_buy')
        route_mto = warehouse1.mto_pull_id.route_id.id
        vendor1 = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        product_1 = self.env['product.product'].create({
            'name': 'product1',
            'is_storable': True,
            'uom_id': unit,
            'seller_ids': [Command.create({
                'partner_id': vendor1.id,
                'price': 50,
            })],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })
        product_2 = self.env['product.product'].create({
            'name': 'product2',
            'is_storable': True,
            'uom_id': unit,
            'seller_ids': [Command.create({
                'partner_id': vendor1.id,
                'price': 50,
            })],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })

        # Blanket orders creation
        line1 = (0, 0, {'product_id': product_1.id, 'product_qty': 18, 'uom_id': product_1.uom_id.id, 'price_unit': 41})
        line2 = (0, 0, {'product_id': product_2.id, 'product_qty': 18, 'uom_id': product_2.uom_id.id, 'price_unit': 42})
        requisition_1 = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'requisition_type': 'blanket_order',
            'vendor_id': vendor1.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_2 = self.env['purchase.requisition'].create({
            'line_ids': [line2],
            'requisition_type': 'blanket_order',
            'vendor_id': vendor1.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_1.action_confirm()
        requisition_2.action_confirm()
        # Stock moves
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        move1 = self.env['stock.move'].create({
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_1.id,
            'uom_id': unit,
            'product_uom_qty': 10.0,
            'price_unit': 100,
        })
        move2 = self.env['stock.move'].create({
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_2.id,
            'uom_id': unit,
            'product_uom_qty': 10.0,
            'price_unit': 100,
        })
        move1._action_confirm()
        move2._action_confirm()
        # Verifications
        POL1 = self.env['purchase.order.line'].search([('product_id', '=', product_1.id)]).order_id
        POL2 = self.env['purchase.order.line'].search([('product_id', '=', product_2.id)]).order_id
        self.assertFalse(POL1 == POL2, 'The two blanket orders should generate two purchase different purchase orders')
        POL1.write({'order_line': [
            (0, 0, {
                'name': product_2.name,
                'product_id': product_2.id,
                'product_qty': 5.0,
                'uom_id': product_2.uom_id.id,
            })
        ]})
        order_line = self.env['purchase.order.line'].search([
            ('product_id', '=', product_2.id),
            ('product_qty', '=', 5.0),
        ])
        self.assertEqual(order_line.price_unit, 50, 'The supplier info chosen should be the one without requisition id')
