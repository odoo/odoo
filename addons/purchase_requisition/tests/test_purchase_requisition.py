# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form
from odoo import fields


class TestPurchaseRequisition(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseRequisition, self).setUp()

        self.product_09_id = self.ref('product.product_product_9')
        self.product_09_uom_id = self.ref('product.product_uom_unit')
        self.product_13_id = self.ref('product.product_product_13')
        self.res_partner_1_id = self.ref('base.res_partner_1')
        self.res_company_id = self.ref('base.main_company')

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
        product.write({'route_ids': [(4, self.ref('purchase.route_warehouse0_buy'))]})
        self.env['procurement.group'].run(product, 14, self.env['product.uom'].browse(self.ref('product.product_uom_unit')), warehouse.lot_stock_id, '/', '/',
                                          {
                                            'warehouse_id': warehouse,
                                            'date_planned': date_planned,
                                          })

        # Check requisition details which created after run procurement.
        line = self.env['purchase.requisition.line'].search([('product_id', '=', self.product_13_id), ('product_qty', '=', 14.0)])
        requisition = line[0].requisition_id
        self.assertEqual(requisition.date_end, date_planned, "End date does not correspond.")
        self.assertEqual(len(requisition.line_ids), 1, "Requisition Lines should be one.")
        self.assertEqual(line.product_uom_id.id, self.ref('product.product_uom_unit'), "UOM is not correspond.")

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

    def test_call_for_tender_mto(self):
        """ Simulate a mto sale order with a call for tender. This
        should create the following objects in this order:
        customer move -> purchase tender -> purchase -> supplier move
        Also this test checks that the supplier move is linked to The
        customer move and the user should able to proccess the
        delivery order to the end.
        In order to check more scenario. This test will generate 2 po
        from the same requisition (purchase tender).
        requisition -> PO1 -> Picking1 -> customer picking
                    -> PO2 -> Picking2 /
        """
        stock_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_stock')
        customer_location = self.env['ir.model.data'].xmlid_to_object('stock.stock_location_customers')
        product = self.env['product.product'].create({
            'name': 'Baby Mop',
            'type': 'product',
            'route_ids': [
                (4, self.ref('stock.route_warehouse0_mto')),
                (4, self.ref('purchase.route_warehouse0_buy'))
            ],
            'categ_id': self.env.ref('product.product_category_all').id,
            'purchase_requisition': 'tenders',
        })
        customer_move = self.env['stock.move'].create({
            'name': 'move out',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 100.0,
            'procure_method': 'make_to_order',
        })
        customer_move._action_confirm()

        purchase_requisition_line = self.env['purchase.requisition.line'].search([('product_id', '=', product.id)])
        purchase_requisition = purchase_requisition_line.requisition_id

        self.assertTrue(purchase_requisition, 'A purchase requisition should created')
        self.assertEqual(purchase_requisition_line.move_dest_id, customer_move, 'The customer move should be fixed on the requisition line.')

        purchase_requisition.action_in_progress()

        # Create two partner for the two purchase order.
        partner_1 = self.env['res.partner'].create({'name': 'Mother Annabelle'})

        purchase_form = Form(self.env['purchase.order'].with_context(default_requisition_id=purchase_requisition.id))
        # Since there is no vendor on the requisition we have to manually set one.
        purchase_form.partner_id = partner_1
        purchase = purchase_form.save()

        self.assertEqual(len(purchase.order_line), 1, 'One order line should be created from the purchase requisition line.')
        self.assertEqual(purchase.order_line.product_id, customer_move.product_id, 'The product should be the same than the product on the move.')
        self.assertEqual(purchase.origin, purchase_requisition.name)
        self.assertEqual(purchase.order_line.move_dest_ids, customer_move, 'The customer move should be fixed on the order line.')

        self.assertEqual(purchase.partner_id, partner_1, 'Partner on the first purchase order should not be modify.')

        # Confirm the purchase order and generate the associated pickings.
        purchase.button_confirm()

        picking = purchase.picking_ids
        self.assertTrue(picking.move_lines, 'A picking should be created for the purchase order with one stock move.')

        self.assertEqual(picking.move_lines, customer_move.move_orig_ids, 'The supplier moves and customer move should be linked.')
