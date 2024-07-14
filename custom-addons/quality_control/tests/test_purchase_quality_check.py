# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_common import TestQualityCommon
from odoo import fields
from odoo.tests import tagged, users


@tagged('post_install', '-at_install')
class TestPurchaseQualityCheck(TestQualityCommon):

    def setUp(self):
        super().setUp()
        if 'purchase.order' not in self.env:
            self.skipTest('`purchase` is not installed')

        self.buyer = self.env['res.users'].create({
            'name': 'Buyer',
            'login': 'buyer',
            'email': 'superbuyer@example.com',
            'groups_id': [
                # Internal
                (4, self.ref('base.group_user')),
                # Purchase: User:
                (4, self.ref('purchase.group_purchase_user')),
            ],
        })

        # Create Quality Point for incoming shipment.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
        })

    @users('buyer')
    def test_purchase_quality_check(self):
        """
        Test that the Quality Check is created with the 'none' status when the PO is confirmed,
        and removed when the PO is cancelled.
        """
        # Create a Purchase Order
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_qty': 1.0,
                    'product_uom': self.product.uom_po_id.id,
                    'price_unit': 1.0,
                    'date_planned': fields.Datetime.now(),
                })]
        })
        po.button_confirm()

        # Check if the incoming shipment is created.
        po_sudo = po.sudo()
        self.assertTrue(po_sudo.picking_ids, "Incoming shipment not created.")

        # Check if the Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(po_sudo.picking_ids.check_ids), 1)
        self.assertEqual(po_sudo.picking_ids.check_ids.quality_state, 'none')

        self.env['stock.move.line'].invalidate_model()
        po.button_cancel()

        # Check that the picking is canceled
        self.assertEqual(po_sudo.picking_ids.state, 'cancel', 'The picking should be canceled after the PO cancellation')
        # Check that the quality check is removed
        self.assertFalse(po_sudo.picking_ids.check_ids, 'The quality check should be removed after the picking cancellation')
