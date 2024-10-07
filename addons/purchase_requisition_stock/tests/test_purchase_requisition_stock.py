# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon


class TestPurchaseRequisitionStock(TestPurchaseRequisitionCommon):

    def test_01_purchase_requisition_stock(self):
        date_planned = fields.Datetime.now()
        warehouse = self.env['stock.warehouse'].browse(self.ref('stock.warehouse0'))
        self.env['procurement.group'].run([self.env['procurement.group'].Procurement(
            self.product_13,
            14,
            self.env['uom.uom'].browse(self.ref('uom.product_uom_unit')),
            warehouse.lot_stock_id,
            '/',
            '/',
            self.env.company,
            {
                'warehouse_id': warehouse,
                'date_planned': date_planned,
            }
        )])
        # Check requisition details which created after run procurement.
        line = self.env['purchase.requisition.line'].search([('product_id', '=', self.product_13.id), ('product_qty', '=', 14.0)])
        requisition = line[0].requisition_id
        self.assertEqual(requisition.date_end, date_planned, "End date does not correspond.")
        self.assertEqual(len(requisition.line_ids), 1, "Requisition Lines should be one.")
        self.assertEqual(line.product_uom_id.id, self.ref('uom.product_uom_unit'), "UOM is not correspond.")

        # Give access rights of Purchase Requisition User to open requisition
        # Set tender state to choose tendering line.
        self.requisition1.with_user(self.user_purchase_requisition_user).action_in_progress()
        self.requisition1.with_user(self.user_purchase_requisition_user).action_open()

        # Vendor send one RFQ so I create a RfQ of that agreement.
        PurchaseOrder = self.env['purchase.order']
        purchase_order = PurchaseOrder.new({'partner_id': self.res_partner_1, 'requisition_id': self.requisition1.id})
        purchase_order._onchange_requisition_id()
        po_dict = purchase_order._convert_to_write({name: purchase_order[name] for name in purchase_order._cache})
        self.po_requisition = PurchaseOrder.create(po_dict)
        self.assertEqual(len(self.po_requisition.order_line), 1, 'Purchase order should have one line')

    def test_02_purchase_requisition_stock(self):
        """Plays with the sequence of regular supplier infos and one created by blanket orders."""
        # Product creation
        unit = self.ref("uom.product_uom_unit")
        warehouse1 = self.env.ref('stock.warehouse0')
        route_buy = self.ref('purchase_stock.route_warehouse0_buy')
        route_mto = warehouse1.mto_pull_id.route_id.id
        vendor1 = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'BBB', 'email': 'from.test2@example.com'})
        supplier_info1 = self.env['product.supplierinfo'].create({
            'name': vendor1.id,
            'price': 50,
        })
        product_test = self.env['product.product'].create({
            'name': 'Usb Keyboard',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
            'seller_ids': [(6, 0, [supplier_info1.id])],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })

        # Stock picking
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        move1 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()

        # Verification : there should be a purchase order created with the good price
        purchase1 = self.env['purchase.order'].search([('partner_id', '=', vendor1.id)])
        self.assertEqual(purchase1.order_line.price_unit, 50, 'The price on the purchase order is not the supplierinfo one')

        # Blanket order creation
        line1 = (0, 0, {'product_id': product_test.id, 'product_qty': 18, 'product_uom_id': product_test.uom_po_id.id, 'price_unit': 50})
        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none',
        })
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'type_id': requisition_type.id,
            'vendor_id': vendor2.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_blanket.action_in_progress()

        # Second stock move
        move2 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10
        })
        move2._action_confirm()

        # As the supplier.info linked to the blanket order has the same price, the first one is stille used.
        self.assertEqual(purchase1.order_line.product_qty, 20)

        # Update the sequence of the blanket order's supplier info.
        supplier_info1.sequence = 2
        requisition_blanket.line_ids.supplier_info_ids.sequence = 1
        # In [13]: [(x.sequence, x.min_qty, x.price, x.name.name) for x in supplier_info1 + requisition_blanket.line_ids.supplier_info_ids]
        # Out[13]: [(2, 0.0, 50.0, 'AAA'), (1, 0.0, 50.0, 'BBB')]

        # Second stock move
        move3 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'product_uom': unit,
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
        supplier_info1 = self.env['product.supplierinfo'].create({
            'name': vendor1.id,
            'price': 50,
        })
        product_1 = self.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
            'seller_ids': [(6, 0, [supplier_info1.id])],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })
        product_2 = self.env['product.product'].create({
            'name': 'product2',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
            'seller_ids': [(6, 0, [supplier_info1.id])],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })
        # Blanket orders creation
        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none',
        })
        line1 = (0, 0, {'product_id': product_1.id, 'product_qty': 18, 'product_uom_id': product_1.uom_po_id.id, 'price_unit': 41, 'product_description_variants': 'BO-1 Custom Description'})
        line2 = (0, 0, {'product_id': product_2.id, 'product_qty': 18, 'product_uom_id': product_2.uom_po_id.id, 'price_unit': 42, 'product_description_variants': 'BO-2 Custom Description'})
        requisition_1 = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'type_id': requisition_type.id,
            'vendor_id': vendor1.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_2 = self.env['purchase.requisition'].create({
            'line_ids': [line2],
            'type_id': requisition_type.id,
            'vendor_id': vendor1.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_1.action_in_progress()
        requisition_2.action_in_progress()
        # Stock moves
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        move1 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_1.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 100,
        })
        move2 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_2.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 100,
        })
        move1._action_confirm()
        move2._action_confirm()
        # Verifications
        po1 = self.env['purchase.order.line'].search([('product_id', '=', product_1.id)]).order_id
        po2 = self.env['purchase.order.line'].search([('product_id', '=', product_2.id)]).order_id
        self.assertFalse(po1 == po2, 'The two blanket orders should generate two purchase different purchase orders')
        self.assertTrue('BO-1 Custom Description' in po1.order_line.name, 'The description of the line in the blanket order should be included in the purchase order line description')
        self.assertTrue('BO-2 Custom Description' in po2.order_line.name, 'The description of the line in the blanket order should be included in the purchase order line description')
        po1.write({'order_line': [
            (0, 0, {
                'name': product_2.name,
                'product_id': product_2.id,
                'product_qty': 5.0,
                'product_uom': product_2.uom_po_id.id,
                'price_unit': 0,
                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            })
        ]})
        order_line = self.env['purchase.order.line'].search([
            ('product_id', '=', product_2.id),
            ('product_qty', '=', 5.0),
        ])
        order_line._onchange_quantity()
        self.assertEqual(order_line.price_unit, 50, 'The supplier info chosen should be the one without requisition id')
