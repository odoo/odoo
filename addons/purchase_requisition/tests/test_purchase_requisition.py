# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon
from odoo import Command
from odoo.tests import Form

from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestPurchaseRequisition(TestPurchaseRequisitionCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPurchaseRequisition, cls).setUpClass()
        cls.env['res.currency.rate'].search([]).unlink()

    def test_00_purchase_requisition_users(self):
        self.assertTrue(self.user_purchase_requisition_manager, 'Manager Should be created')
        self.assertTrue(self.user_purchase_requisition_user, 'User Should be created')

    def test_01_cancel_purchase_requisition(self):
        self.bo_requisition.with_user(self.user_purchase_requisition_user).action_cancel()
        # Check requisition after cancelled.
        self.assertEqual(self.bo_requisition.state, 'cancel', 'Requisition should be in cancelled state.')
        # I reset requisition as "New".
        self.bo_requisition.with_user(self.user_purchase_requisition_user).action_draft()
        # I duplicate requisition.
        self.bo_requisition.with_user(self.user_purchase_requisition_user).copy()

    def test_02_purchase_requisition(self):
        price_product09 = 34
        price_product13 = 62
        quantity = 26

        # Create a pruchase requisition with type blanket order and two product
        line1 = (0, 0, {'product_id': self.product_09.id, 'product_qty': quantity, 'uom_id': self.product_uom_id.id, 'price_unit': price_product09})
        line2 = (0, 0, {'product_id': self.product_13.id, 'product_qty': quantity, 'uom_id': self.product_uom_id.id, 'price_unit': price_product13})

        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1, line2],
            'requisition_type': 'blanket_order',
            'vendor_id': self.res_partner_1.id,
        })

        # confirm the requisition
        requisition_blanket.action_confirm()

        # Check for both product that the new supplier info(purchase.requisition.vendor_id) is added to the purchase tab
        # and check the quantity
        seller_partner1 = self.res_partner_1
        supplierinfo09 = self.env['product.supplierinfo'].search([
            ('partner_id', '=', seller_partner1.id),
            ('product_id', '=', self.product_09.id),
            ('purchase_requisition_id', '=', requisition_blanket.id),
        ])
        self.assertEqual(supplierinfo09.partner_id, seller_partner1, 'The supplierinfo is not correct')
        self.assertEqual(supplierinfo09.price, price_product09, 'The supplierinfo is not correct')

        supplierinfo13 = self.env['product.supplierinfo'].search([
            ('partner_id', '=', seller_partner1.id),
            ('product_id', '=', self.product_13.id),
            ('purchase_requisition_id', '=', requisition_blanket.id),
        ])
        self.assertEqual(supplierinfo13.partner_id, seller_partner1, 'The supplierinfo is not correct')
        self.assertEqual(supplierinfo13.price, price_product13, 'The supplierinfo is not correct')

        # Put the requisition in done Status
        requisition_blanket.action_confirm()
        requisition_blanket.action_done()

        self.assertFalse(self.env['product.supplierinfo'].search([('id', '=', supplierinfo09.id)]), 'The supplier info should be removed')
        self.assertFalse(self.env['product.supplierinfo'].search([('id', '=', supplierinfo13.id)]), 'The supplier info should be removed')

    def test_03_blanket_order_rfq(self):
        """ Create a blanket order + an RFQ for it """

        bo_form = Form(self.env['purchase.requisition'])
        bo_form.vendor_id = self.res_partner_1
        bo_form.requisition_type = 'blanket_order'
        with bo_form.line_ids.new() as line:
            line.product_id = self.product_09
            line.product_qty = 5.0
            line.price_unit = 21
        bo = bo_form.save()
        bo.action_confirm()

        # lazy reproduction of clicking on "New Quotation" act_window button
        po_form = Form(self.env['purchase.order'].with_context({"default_requisition_id": bo.id, "default_user_id": False}))
        po = po_form.save()

        self.assertEqual(po.order_line.price_unit, bo.line_ids.price_unit, 'The blanket order unit price should have been copied to purchase order')
        self.assertEqual(po.partner_id, bo.vendor_id, 'The blanket order vendor should have been copied to purchase order')

        po_form = Form(po)
        po_form.order_line.remove(0)
        with po_form.order_line.new() as line:
            line.product_id = self.product_09
            line.product_qty = 5.0

        po = po_form.save()
        po.button_confirm()
        self.assertEqual(po.order_line.price_unit, bo.line_ids.price_unit, 'The blanket order unit price should still be copied to purchase order')
        self.assertEqual(po.state, "purchase")

    def test_06_purchase_requisition(self):
        """ Create a blanket order for a product and a vendor already linked via
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
            'partner_id': vendor.id,
        })

        # create an empty blanket order
        line1 = (0, 0, {
            'product_id': product2.id,
            'uom_id': product2.uom_id.id,
            'price_unit': 41,
            'product_qty': 10,
        })
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'requisition_type': 'blanket_order',
            'vendor_id': vendor.id,
        })
        requisition_blanket.action_confirm()
        self.env['purchase.requisition.line'].create({
            'product_id': product.id,
            'product_qty': 14.0,
            'requisition_id': requisition_blanket.id,
            'price_unit': 10,
        })
        new_si = self.env['product.supplierinfo'].search([
            ('product_id', '=', product.id),
            ('partner_id', '=', vendor.id)
        ]) - supplier_info
        self.assertEqual(new_si.purchase_requisition_id, requisition_blanket, 'the blanket order is not linked to the supplier info')

    def test_08_purchase_requisition_sequence(self):
        new_company = self.env['res.company'].create({'name': 'Company 2'})
        self.env['ir.sequence'].create({
            'code': 'purchase.requisition.blanket.order',
            'prefix': 'REQ_',
            'name': 'Blanket Order sequence',
            'company_id': new_company.id,
        })
        self.bo_requisition.company_id = new_company
        self.bo_requisition.line_ids.write({'price_unit': 10.0})
        self.bo_requisition.action_confirm()
        self.assertTrue(self.bo_requisition.name.startswith("REQ_"))

    def test_09_purchase_template(self):
        """ Create a Purchase Template + an RFQ for it """

        self.supplierinfo10 = self.env['product.supplierinfo'].create({
            'partner_id': self.res_partner_1.id,
            'product_id': self.product_09.id,
            'price': 15.0,
            'min_qty': 2.0,
        })

        # Create a purchase requisition with type purchase template and two products
        line1 = Command.create({'product_id': self.product_09.id, 'uom_id': self.product_uom_id.id})
        line2 = Command.create({'product_id': self.product_13.id, 'uom_id': self.product_uom_id.id})

        purchase_template = self.env['purchase.requisition'].create({
            'line_ids': [line1, line2],
            'requisition_type': 'purchase_template',
            'vendor_id': self.res_partner_1.id,
        })

        # update the product_qty to get the Unit price
        purchase_template.line_ids[0].product_qty = 2.0
        purchase_template.line_ids[1].product_qty = 1.0
        self.assertEqual(purchase_template.line_ids[0].price_unit, self.supplierinfo10.price, 'Unit Price should match supplierinfo price')
        self.assertEqual(purchase_template.line_ids[1].price_unit, self.product_13.standard_price, 'Unit Price should equal standard_price when no supplierinfo')

        purchase_template.action_confirm()

        po_form = Form(self.env['purchase.order'].with_context({"default_requisition_id": purchase_template.id, "default_user_id": False}))
        po = po_form.save()
        self.assertEqual(po.partner_id, purchase_template.vendor_id, 'The purchase template vendor should have been copied to purchase order')
        self.assertEqual(po.order_line[0].price_unit, purchase_template.line_ids[0].price_unit, 'The purchase template unit price should have been copied to purchase order')
        self.assertEqual(po.order_line[0].product_qty, purchase_template.line_ids[0].product_qty, 'The purchase template product quantity should have been copied to purchase order')
        self.assertEqual(po.order_line[1].price_unit, purchase_template.line_ids[1].price_unit, 'The purchase template unit price should have been copied to purchase order')
        self.assertEqual(po.order_line[1].product_qty, purchase_template.line_ids[1].product_qty, 'The purchase template product quantity should have been copied to purchase order')

    def test_purchase_requisition_with_same_product(self):
        """
        Create two requisitions with the same product, but only one of them has a PO linked.
        Check that the ordered quantity is correctly computed.
        """
        self.bo_requisition.vendor_id = self.res_partner_1
        self.bo_requisition.requisition_type = 'purchase_template'
        requisition_2 = self.bo_requisition.copy({'name': 'requisition_2'})
        # Create purchase order from purchase requisition
        po_form = Form(self.env['purchase.order'].with_context(default_requisition_id=requisition_2.id))
        po = po_form.save()
        self.assertEqual(po.requisition_id, requisition_2)
        po.button_confirm()
        self.assertEqual(po.state, 'purchase')
        (self.bo_requisition.line_ids | requisition_2.line_ids)._compute_ordered_qty()
        self.assertEqual(self.bo_requisition.line_ids.qty_ordered, 0)
        self.assertEqual(requisition_2.line_ids.qty_ordered, 10)

    def test_purchase_order_taxes_from_purchase_agreement_in_child_company(self):
        """
        Ensure that the taxes of the parent company are applied to the PO generated from purchase agreement in the child company.
        """
        child_company = self.env['res.company'].create({
            'name': 'My Branch',
            'parent_id': self.env.company.id,
        })
        # Ensure all the tax on the product are from the parent company
        self.product_09.supplier_taxes_id = self.env['account.tax'].create({
            'name': 'Test Tax 10%',
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'purchase',
            'company_id': self.env.company.id,
        })

        purchase_requisition = self.env['purchase.requisition'].with_company(child_company.id).create({
            'vendor_id': self.res_partner_1.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_09.id,
                    'product_qty': 5.0,
                    'price_unit': 20,
                }),
            ],
        })
        purchase_requisition.action_confirm()

        po_form = Form(self.env['purchase.order'].with_company(child_company.id))
        po_form.requisition_id = purchase_requisition
        po = po_form.save()
        self.assertEqual(po.partner_id, purchase_requisition.vendor_id, 'The partner should have been set from the purchase requisition')
        self.assertEqual(po.order_line.price_unit, purchase_requisition.line_ids.price_unit, 'The unit price should have been set from the purchase requisition')
        self.assertEqual(po.order_line.tax_ids, purchase_requisition.line_ids.product_id.supplier_taxes_id, 'The blanket order taxes should have been set')
