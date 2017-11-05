# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
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
