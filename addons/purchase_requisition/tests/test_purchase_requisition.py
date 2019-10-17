# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo import fields
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestPurchaseRequisition(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseRequisition, self).setUp()

        self.product_09_id = self.ref('product.product_product_9')
        self.product_09_uom_id = self.ref('uom.product_uom_unit')
        self.product_13_id = self.ref('product.product_product_13')
        self.res_partner_1_id = self.ref('base.res_partner_1')
        self.res_company_id = self.ref('base.main_company')
        self.env.user.company_id.currency_id = self.env.ref("base.USD").id

        self.ResUser = self.env['res.users']
        # Create a user as 'Purchase Requisition Manager'
        self.res_users_purchase_requisition_manager = self.ResUser.create({'company_id': self.res_company_id, 'name': 'Purchase requisition Manager', 'login': 'prm', 'email': 'requisition_manager@yourcompany.com'})
        # Added groups for Purchase Requisition Manager.
        self.res_users_purchase_requisition_manager.group_id = self.ref('purchase.group_purchase_manager')
        # Create a user as 'Purchase Requisition User'
        self.res_users_purchase_requisition_user = self.ResUser.create({'company_id': self.res_company_id, 'name': 'Purchase requisition User', 'login': 'pru', 'email': 'requisition_user@yourcompany.com'})
        # Added groups for Purchase Requisition User.
        self.res_users_purchase_requisition_user.group_id = self.ref('purchase.group_purchase_user')

        # In order to test process of the purchase requisition ,create requisition
        self.requisition1 = self.env['purchase.requisition'].create({'line_ids': [(0, 0, {'product_id': self.product_09_id, 'product_qty': 10.0, 'product_uom_id': self.product_09_uom_id})]})

    def test_00_purchase_requisition_users(self):
        self.assertTrue(self.res_users_purchase_requisition_manager, 'Manager Should be created')
        self.assertTrue(self.res_users_purchase_requisition_user, 'User Should be created')

    def test_01_cancel_purchase_requisition(self):
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).action_cancel()
        # Check requisition after cancelled.
        self.assertEqual(self.requisition1.state, 'cancel', 'Requisition should be in cancelled state.')
        # I reset requisition as "New".
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).action_draft()
        # I duplicate requisition.
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).copy()

    def test_02_purchase_requisition(self):
        date_planned = fields.Datetime.now()
        warehouse = self.env['stock.warehouse'].browse(self.ref('stock.warehouse0'))
        product = self.env['product.product'].browse(self.product_13_id)
        product.write({'route_ids': [(4, self.ref('purchase_stock.route_warehouse0_buy'))]})
        self.env['procurement.group'].run(product, 14, self.env['uom.uom'].browse(self.ref('uom.product_uom_unit')), warehouse.lot_stock_id, '/', '/',
                                          {
                                            'warehouse_id': warehouse,
                                            'date_planned': date_planned,
                                          })

        # Check requisition details which created after run procurement.
        line = self.env['purchase.requisition.line'].search([('product_id', '=', self.product_13_id), ('product_qty', '=', 14.0)])
        requisition = line[0].requisition_id
        self.assertEqual(requisition.date_end, date_planned, "End date does not correspond.")
        self.assertEqual(len(requisition.line_ids), 1, "Requisition Lines should be one.")
        self.assertEqual(line.product_uom_id.id, self.ref('uom.product_uom_unit'), "UOM is not correspond.")

        # Give access rights of Purchase Requisition User to open requisition
        # Set tender state to choose tendering line.
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).action_in_progress()
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).action_open()

        # Vendor send one RFQ so I create a RfQ of that agreement.
        PurchaseOrder = self.env['purchase.order']
        purchase_order = PurchaseOrder.new({'partner_id': self.res_partner_1_id, 'requisition_id': self.requisition1.id})
        purchase_order._onchange_requisition_id()
        po_dict = purchase_order._convert_to_write({name: purchase_order[name] for name in purchase_order._cache})
        self.po_requisition = PurchaseOrder.create(po_dict)
        self.assertEqual(len(self.po_requisition.order_line), 1, 'Purchase order should have one line')

    def test_03_purchase_requisition(self):
        price_product09 = 34
        price_product13 = 62
        quantity = 26
        # Create a pruchase requisition with type blanket order and two product
        line1 = (0, 0, {'product_id': self.product_09_id, 'product_qty': quantity, 'product_uom_id': self.product_09_uom_id, 'price_unit': price_product09})

        self.product_13_uom_id = self.ref('uom.product_uom_unit')
        line2 = (0, 0, {'product_id': self.product_13_id, 'product_qty': quantity, 'product_uom_id': self.product_13_uom_id, 'price_unit': price_product13})

        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none'
        })
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1, line2],
            'type_id': requisition_type.id,
            'vendor_id': self.res_partner_1_id
        })

        # confirm the requisition
        requisition_blanket.action_in_progress()

        # Check for both product that the new supplier info(purchase.requisition.vendor_id) is added to the puchase tab
        # and check the quantity
        seller_partner1 = self.env['res.partner'].browse(self.res_partner_1_id)
        supplierinfo09 = self.env['product.supplierinfo'].search([
            ('name', '=', seller_partner1.id),
            ('product_id', '=', self.product_09_id),
            ('purchase_requisition_id', '=', requisition_blanket.id),
        ])
        self.assertEqual(supplierinfo09.name, seller_partner1, 'The supplierinfo is not the good one')
        self.assertEqual(supplierinfo09.price, price_product09, 'The supplierinfo is not the good one')

        supplierinfo13 = self.env['product.supplierinfo'].search([
            ('name', '=', seller_partner1.id),
            ('product_id', '=', self.product_13_id),
            ('purchase_requisition_id', '=', requisition_blanket.id),
        ])
        self.assertEqual(supplierinfo13.name, seller_partner1, 'The supplierinfo is not the good one')
        self.assertEqual(supplierinfo13.price, price_product13, 'The supplierinfo is not the good one')

        # Put the requisition in done Status
        requisition_blanket.action_in_progress()
        requisition_blanket.action_done()

        self.assertFalse(self.env['product.supplierinfo'].search([('id', '=', supplierinfo09.id)]), 'The supplier info should be removed')
        self.assertFalse(self.env['product.supplierinfo'].search([('id', '=', supplierinfo13.id)]), 'The supplier info should be removed')

    def test_04_purchase_requisition(self):
        """ Set a static supplier info and make a delivery order for a "to buy" product, check that the purchase order created is consistent. Create a blanket order for this product, create a new delivery order for this product and check that the create purchase order set its values according to the blanket order.
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
        line1 = (0, 0, {'product_id': product_test.id, 'product_qty': 18, 'product_uom_id': product_test.uom_po_id.id, 'price_unit': 42})
        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none',
        })
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'type_id': requisition_type.id,
            'vendor_id': vendor1.id,
            'currency_id': self.env.ref("base.USD").id,
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

        # Verifications
        purchase2 = self.env['purchase.order'].search([('partner_id', '=', vendor1.id), ('requisition_id', '=', requisition_blanket.id)])
        self.assertEqual(purchase2.order_line.price_unit, 42, 'The price on the purchase order is not the blanquet order one')

    def test_05_purchase_requisition(self):
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
        line1 = (0, 0, {'product_id': product_1.id, 'product_qty': 18, 'product_uom_id': product_1.uom_po_id.id, 'price_unit': 41})
        line2 = (0, 0, {'product_id': product_2.id, 'product_qty': 18, 'product_uom_id': product_2.uom_po_id.id, 'price_unit': 42})
        requisition_1 = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'type_id': requisition_type.id,
            'vendor_id': vendor1.id,
            'currency_id': self.env.ref("base.USD").id,
        })
        requisition_2 = self.env['purchase.requisition'].create({
            'line_ids': [line2],
            'type_id': requisition_type.id,
            'vendor_id': vendor1.id,
            'currency_id': self.env.ref("base.USD").id,
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
        POL1 = self.env['purchase.order.line'].search([('product_id', '=', product_1.id)]).order_id
        POL2 = self.env['purchase.order.line'].search([('product_id', '=', product_2.id)]).order_id
        self.assertFalse(POL1 == POL2, 'The two blanket orders should generate two purchase different purchase orders')
        POL1.write({'order_line': [
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

    def test_06_purchase_requisition(self):
        """ Create a blanquet order for a product and a vendor already linked via
        a supplier info"""
        product = self.env['product.product'].create({
            'name': 'test6',
        })
        product2 = self.env['product.product'].create({
            'name': 'test6',
        })
        vendor = self.env['res.partner'].create({
            'name': 'vendor6',
        })
        supplier_info = self.env['product.supplierinfo'].create({
            'product_id': product.id,
            'name': vendor.id,
        })

        # create a empty blanquet order
        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none'
        })
        line1 = (0, 0, {
            'product_id': product2.id,
            'product_uom_id': product2.uom_po_id.id,
            'price_unit': 41,
            'product_qty': 10,
        })
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'type_id': requisition_type.id,
            'vendor_id': vendor.id,
        })
        requisition_blanket.action_in_progress()
        self.env['purchase.requisition.line'].create({
            'product_id': product.id,
            'product_qty': 14.0,
            'requisition_id': requisition_blanket.id,
            'price_unit': 10,
        })
        new_si = self.env['product.supplierinfo'].search([
            ('product_id', '=', product.id),
            ('name', '=', vendor.id)
        ]) - supplier_info
        self.assertEqual(new_si.purchase_requisition_id, requisition_blanket, 'the blanket order is not linked to the supplier info')
