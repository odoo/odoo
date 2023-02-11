# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon
from odoo.tests import Form


class TestPurchaseRequisition(TestPurchaseRequisitionCommon):

    def test_00_purchase_requisition_users(self):
        self.assertTrue(self.user_purchase_requisition_manager, 'Manager Should be created')
        self.assertTrue(self.user_purchase_requisition_user, 'User Should be created')

    def test_01_cancel_purchase_requisition(self):
        self.requisition1.with_user(self.user_purchase_requisition_user).action_cancel()
        # Check requisition after cancelled.
        self.assertEqual(self.requisition1.state, 'cancel', 'Requisition should be in cancelled state.')
        # I reset requisition as "New".
        self.requisition1.with_user(self.user_purchase_requisition_user).action_draft()
        # I duplicate requisition.
        self.requisition1.with_user(self.user_purchase_requisition_user).copy()


    def test_02_purchase_requisition(self):
        price_product09 = 34
        price_product13 = 62
        quantity = 26

        # Create a pruchase requisition with type blanket order and two product
        line1 = (0, 0, {'product_id': self.product_09.id, 'product_qty': quantity, 'product_uom_id': self.product_uom_id.id, 'price_unit': price_product09})
        line2 = (0, 0, {'product_id': self.product_13.id, 'product_qty': quantity, 'product_uom_id': self.product_uom_id.id, 'price_unit': price_product13})

        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none'
        })
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1, line2],
            'type_id': requisition_type.id,
            'vendor_id': self.res_partner_1.id,
        })

        # confirm the requisition
        requisition_blanket.action_in_progress()

        # Check for both product that the new supplier info(purchase.requisition.vendor_id) is added to the puchase tab
        # and check the quantity
        seller_partner1 = self.res_partner_1
        supplierinfo09 = self.env['product.supplierinfo'].search([
            ('name', '=', seller_partner1.id),
            ('product_id', '=', self.product_09.id),
            ('purchase_requisition_id', '=', requisition_blanket.id),
        ])
        self.assertEqual(supplierinfo09.name, seller_partner1, 'The supplierinfo is not the good one')
        self.assertEqual(supplierinfo09.price, price_product09, 'The supplierinfo is not the good one')

        supplierinfo13 = self.env['product.supplierinfo'].search([
            ('name', '=', seller_partner1.id),
            ('product_id', '=', self.product_13.id),
            ('purchase_requisition_id', '=', requisition_blanket.id),
        ])
        self.assertEqual(supplierinfo13.name, seller_partner1, 'The supplierinfo is not the good one')
        self.assertEqual(supplierinfo13.price, price_product13, 'The supplierinfo is not the good one')

        # Put the requisition in done Status
        requisition_blanket.action_in_progress()
        requisition_blanket.action_done()

        self.assertFalse(self.env['product.supplierinfo'].search([('id', '=', supplierinfo09.id)]), 'The supplier info should be removed')
        self.assertFalse(self.env['product.supplierinfo'].search([('id', '=', supplierinfo13.id)]), 'The supplier info should be removed')

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

    def test_07_purchase_requisition(self):
        """
            Check that the analytic account and the account tag defined in the purchase requisition line
            is used in the purchase order line when creating a PO.
        """
        analytic_account = self.env['account.analytic.account'].create({'name': 'test_analytic_account'})
        analytic_tag = self.env['account.analytic.tag'].create({'name': 'test_analytic_tag'})
        self.assertEqual(len(self.requisition1.line_ids), 1)
        self.requisition1.line_ids[0].write({
            'account_analytic_id': analytic_account,
            'analytic_tag_ids': analytic_tag,
        })
        # Create purchase order from purchase requisition
        po_form = Form(self.env['purchase.order'].with_context(default_requisition_id=self.requisition1.id))
        po_form.partner_id = self.res_partner_1
        po = po_form.save()
        self.assertEqual(po.order_line.account_analytic_id.id, analytic_account.id, 'The analytic account defined in the purchase requisition line must be the same as the one from the purchase order line.')
        self.assertEqual(po.order_line.analytic_tag_ids.id, analytic_tag.id, 'The analytic account tag defined in the purchase requisition line must be the same as the one from the purchase order line.')
