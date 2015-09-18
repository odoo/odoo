# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon


class TestPurchaseRequisitionDemo(TestPurchaseRequisitionCommon):

    def setUp(self):
        super(TestPurchaseRequisitionDemo, self).setUp()
        self.product_09_id = self.ref('product.product_product_9')
        self.product_09_uom_id = self.ref('product.product_uom_unit')

    def test_00_requisition_demo(self):
        # In order to test process of the purchase requisition ,create requisition
        self.requisition1 = self.PurchaseRequisition.create({'exclusive': 'exclusive', 'line_ids': [(0, 0, {'product_id': self.product_09_id, 'product_qty': 10.0, 'product_uom_id': self.product_09_uom_id})]})
