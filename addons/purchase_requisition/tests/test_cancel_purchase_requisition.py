# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon


class TestCancelPurchaseRequisition(TestPurchaseRequisitionCommon):

    def setUp(self):
        super(TestCancelPurchaseRequisition, self).setUp()
        self.product_09_id = self.ref('product.product_product_9')
        self.product_09_uom_id = self.ref('product.product_uom_unit')
        self.requisition1 = self.PurchaseRequisition.create({'exclusive': 'exclusive', 'line_ids': [(0, 0, {'product_id': self.product_09_id, 'product_qty': 10.0, 'product_uom_id': self.product_09_uom_id})]})

    def test_00_cancel_purchase_requisition(self):

        # Cancel requisition.
        self.requisition1.tender_cancel()
        # Check requisition after cancelled.
        self.assertEqual(self.requisition1.state, 'cancel', 'Requisition should be in cancelled state.')
        # Reset requisition as "New".
        self.requisition1.tender_reset()
        # Duplicate requisition.
        self.requisition1.copy()
