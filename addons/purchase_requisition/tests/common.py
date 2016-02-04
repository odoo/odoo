# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestPurchaseRequisitionCommon(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseRequisitionCommon, self).setUp()

        # Object data
        self.MakeProcurement = self.env['make.procurement']
        self.ProcurementOrder = self.env['procurement.order']
        self.PurchaseOrder = self.env['purchase.order']
        self.PurchaseRequisition = self.env['purchase.requisition']
        self.PurchaseRequisitionPartner = self.env['purchase.requisition.partner']
        self.ResUser = self.env['res.users']

        # Model data
        self.product_13_id = self.ref('product.product_product_13')
        self.request_for_quote = self.env.ref('purchase_requisition.rfq2')
        self.requisition_01 = self.env.ref('purchase_requisition.requisition1')
        self.res_partner_12_id = self.ref('base.res_partner_12')
        self.res_company_id = self.ref('base.main_company')
