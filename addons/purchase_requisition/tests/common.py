# -*- coding: utf-8 -*-

from odoo.tests import common


class TestPurchaseRequisitionCommon(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseRequisitionCommon, self).setUp()

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
