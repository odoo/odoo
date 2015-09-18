# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon
from odoo.tools import float_compare


class TestPurchaseRequisition(TestPurchaseRequisitionCommon):

    def setUp(self):
        super(TestPurchaseRequisition, self).setUp()
        self.product_09_id = self.ref('product.product_product_9')
        self.product_09_uom_id = self.ref('product.product_uom_unit')
        self.requisition1 = self.PurchaseRequisition.create({'exclusive': 'exclusive', 'line_ids': [(0, 0, {'product_id': self.product_09_id, 'product_qty': 10.0, 'product_uom_id': self.product_09_uom_id})]})
        # Create User
        self.res_users_purchase_requisition_user = self.ResUser.create({'company_id': self.res_company_id, 'name': 'Purchase requisition User', 'login': 'pru', 'email': 'requisition_user@yourcompany.com'})
        # Added groups for Purchase Requisition User.
        self.res_users_purchase_requisition_user.group_id = self.ref('purchase.group_purchase_user')
        # Create a user as 'Purchase Requisition Manager'
        self.res_users_purchase_requisition_manager = self.ResUser.create({'company_id': self.res_company_id, 'name': 'Purchase requisition Manager', 'login': 'prm', 'email': 'requisition_manager@yourcompany.com'})
        # Added groups for Purchase Requisition Manager.
        self.res_users_purchase_requisition_manager.group_id = self.ref('purchase.group_purchase_manager')

    def test_00_purchase_requisition(self):
        # Create the procurement order and run that procurement.
        procurement_product_hdd3 = self.MakeProcurement.create({'product_id': self.product_13_id, 'qty': 15, 'uom_id': self.ref('product.product_uom_unit'), 'warehouse_id': self.ref('stock.warehouse0')})
        procurement_product_hdd3.make_procurement()
        # Run the scheduler.
        self.ProcurementOrder.run_scheduler()
        # Check requisition details which created after run procurement.
        procurements = self.ProcurementOrder.search([('requisition_id', '!=', False)])
        for procurement in procurements:
            requisition = procurement.requisition_id
            self.assertEqual(requisition.date_end, procurement.date_planned, "End date is not correspond.")
            self.assertEqual(len(requisition.line_ids), 1, "Requisition Lines should be one.")
            line = requisition.line_ids[0]
            self.assertEqual(line.product_id.id, procurement.product_id.id, "Product is not correspond.")
            self.assertEqual(line.product_uom_id.id, procurement.product_uom.id, "UOM is not correspond.")
            self.assertEqual(float_compare(line.product_qty, procurement.product_qty, precision_digits=2), 0, "Quantity is not correspond.")
        # Send the purchase order associated to the requisition.
        for element in self.requisition1:
            element.purchase_ids.write({'state': 'sent'})
        # Give access rights of Purchase Requisition User to open requisition
        # Open another requisition and set tender state to choose tendering line.
        self.requisition1.with_context({'uid': self.res_users_purchase_requisition_user.id}).tender_in_progress()
        self.requisition1.with_context({'uid': self.res_users_purchase_requisition_user.id}).tender_open()
        # Vendor send one RFQ so I create requisition request of that supplier.
        requisition_partner_0 = self.PurchaseRequisitionPartner.create(dict(partner_ids=[(6, 0, [self.res_partner_12_id])]))
        requisition_partner_0.with_context({"active_model": "purchase.requisition", "active_ids": [self.requisition1.id], "active_id": self.requisition1.id, 'uid': 'res_users_purchase_requisition_user', 'mail_create_nolog': True}).create_order()
        # Check that the RFQ details which created for supplier.
        purchase = self.PurchaseOrder.search([('requisition_id', '=', self.requisition1.id)], limit=1)
        self.assertTrue(purchase, "RFQ is not created.")
        self.assertEqual(purchase.partner_id.id, self.res_partner_12_id, 'Purchase should res_partner_12')
        # Confirmed RFQ which has best price.
        purchase.button_confirm()
        # Check status of requisition after confirmed best RFQ.
        self.assertEqual(self.requisition1.state, 'done', 'Purchase requisition should be in done state')
