# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon
from odoo import Command
from odoo.tests import Form

from datetime import timedelta


class TestPurchaseRequisition(TestPurchaseRequisitionCommon):

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
        requisition_blanket.action_in_progress()
        requisition_blanket.action_done()

        self.assertFalse(self.env['product.supplierinfo'].search([('id', '=', supplierinfo09.id)]), 'The supplier info should be removed')
        self.assertFalse(self.env['product.supplierinfo'].search([('id', '=', supplierinfo13.id)]), 'The supplier info should be removed')

    def test_03_blanket_order_rfq(self):
        """ Create a blanket order + an RFQ for it """
        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none'
        })

        bo_form = Form(self.env['purchase.requisition'])
        bo_form.vendor_id = self.res_partner_1
        bo_form.type_id = requisition_type
        with bo_form.line_ids.new() as line:
            line.product_id = self.product_09
            line.product_qty = 5.0
            line.price_unit = 21
        bo = bo_form.save()
        bo.action_in_progress()

        # lazy reproduction of clicking on "New Quotation" act_window button
        po_form = Form(self.env['purchase.order'].with_context({"default_requisition_id": bo.id, "default_user_id": False}))
        po = po_form.save()
        po.button_confirm()
        self.assertEqual(po.order_line.price_unit, bo.line_ids.price_unit, 'The blanket order unit price should have been copied to purchase order')
        self.assertEqual(po.partner_id, bo.vendor_id, 'The blanket order vendor should have been copied to purchase order')

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
            ('partner_id', '=', vendor.id)
        ]) - supplier_info
        self.assertEqual(new_si.purchase_requisition_id, requisition_blanket, 'the blanket order is not linked to the supplier info')

    def test_07_alternative_purchases_wizards(self):
        """Directly link POs to each other as 'Alternatives': check that wizards and
        their flows correctly work."""
        orig_po = self.env['purchase.order'].create({
            'partner_id': self.res_partner_1.id,
        })
        unit_price = 50
        po_form = Form(orig_po)
        with po_form.order_line.new() as line:
            line.product_id = self.product_09
            line.product_qty = 5.0
            line.price_unit = unit_price
            line.product_uom = self.env.ref('uom.product_uom_dozen')
        with po_form.order_line.new() as line:
            line.display_type = "line_section"
            line.name = "Products"
        with po_form.order_line.new() as line:
            line.display_type = 'line_note'
            line.name = 'note1'
        po_form.save()

        # first flow: check that creating an alt PO correctly auto-links both POs to each other
        action = orig_po.action_create_alternative()
        alt_po_wiz = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wiz.partner_id = self.res_partner_1
        alt_po_wiz.copy_products = True
        alt_po_wiz = alt_po_wiz.save()
        alt_po_wiz.action_create_alternative()
        self.assertEqual(len(orig_po.alternative_po_ids), 2, "Original PO should be auto-linked to itself and newly created PO")

        # check alt po was created with correct values
        alt_po_1 = orig_po.alternative_po_ids.filtered(lambda po: po.id != orig_po.id)
        self.assertEqual(len(alt_po_1.order_line), 3)
        self.assertEqual(orig_po.order_line[0].product_id, alt_po_1.order_line[0].product_id, "Alternative PO should have copied the product to purchase from original PO")
        self.assertEqual(orig_po.order_line[0].product_qty, alt_po_1.order_line[0].product_qty, "Alternative PO should have copied the qty to purchase from original PO")
        self.assertEqual(orig_po.order_line[0].product_uom, alt_po_1.order_line[0].product_uom, "Alternative PO should have copied the product unit of measure from original PO")
        self.assertEqual((orig_po.order_line[1].display_type, orig_po.order_line[1].name), (alt_po_1.order_line[1].display_type, alt_po_1.order_line[1].name))
        self.assertEqual((orig_po.order_line[2].display_type, orig_po.order_line[2].name), (alt_po_1.order_line[2].display_type, alt_po_1.order_line[2].name))
        self.assertEqual(len(alt_po_1.alternative_po_ids), 2, "Newly created PO should be auto-linked to itself and original PO")

        # check compare POLs correctly calcs best date/price PO lines: orig_po.date_planned = best & alt_po.price = best
        alt_po_1.order_line[0].date_planned += timedelta(days=1)
        alt_po_1.order_line[0].price_unit = unit_price - 10
        action = orig_po.action_compare_alternative_lines()
        best_price_ids, best_date_ids, best_price_unit_ids = orig_po.get_tender_best_lines()
        best_price_pol = self.env['purchase.order.line'].browse(best_price_ids)
        best_date_pol = self.env['purchase.order.line'].browse(best_date_ids)
        best_unit_price_pol = self.env['purchase.order.line'].browse(best_price_unit_ids)
        self.assertEqual(best_price_pol.order_id.id, alt_po_1.id, "Best price PO line was not correctly calculated")
        self.assertEqual(best_date_pol.order_id.id, orig_po.id, "Best date PO line was not correctly calculated")
        self.assertEqual(best_unit_price_pol.order_id.id, alt_po_1.id, "Best unit price PO line was not correctly calculated")

        # second flow: create extra alt PO, check that all 3 POs are correctly auto-linked
        action = orig_po.action_create_alternative()
        alt_po_wiz = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wiz.partner_id = self.res_partner_1
        alt_po_wiz.copy_products = True
        alt_po_wiz = alt_po_wiz.save()
        alt_po_wiz.action_create_alternative()
        self.assertEqual(len(orig_po.alternative_po_ids), 3, "Original PO should be auto-linked to newly created alternative PO")
        self.assertEqual(len(alt_po_1.alternative_po_ids), 3, "Alternative PO should be auto-linked to newly created alternative PO")
        alt_po_2 = orig_po.alternative_po_ids.filtered(lambda po: po.id not in [alt_po_1.id, orig_po.id])
        self.assertEqual(len(alt_po_2.alternative_po_ids), 3, "All alternative POs should be auto-linked to each other")

        # third flow: confirm one of the POs when alt POs are a mix of confirmed + RFQs
        alt_po_2.write({'state': 'purchase'})
        action = orig_po.button_confirm()
        warning_wiz = Form(self.env['purchase.requisition.alternative.warning'].with_context(**action['context']))
        warning_wiz = warning_wiz.save()
        self.assertEqual(warning_wiz.alternative_po_count, 1, "POs not in a RFQ status should not be listed as possible to cancel")
        warning_wiz.action_cancel_alternatives()
        self.assertEqual(alt_po_1.state, 'cancel', "Alternative PO should have been cancelled")
        self.assertEqual(orig_po.state, 'purchase', "Original PO should have been confirmed")

    def test_08_purchases_multi_linkages(self):
        """Directly link POs to each other as 'Alternatives': check linking/unlinking
        POs that are already linked correctly work."""
        pos = []
        for _ in range(5):
            pos += self.env['purchase.order'].create({
                'partner_id': self.res_partner_1.id,
            }).ids
        pos = self.env['purchase.order'].browse(pos)
        po_1, po_2, po_3, po_4, po_5 = pos

        po_1.alternative_po_ids |= po_2
        po_3.alternative_po_ids |= po_4
        groups = self.env['purchase.order.group'].search([('order_ids', 'in', pos.ids)])
        self.assertEqual(len(po_1.alternative_po_ids), 2, "PO1 and PO2 should only be linked to each other")
        self.assertEqual(len(po_3.alternative_po_ids), 2, "PO3 and PO4 should only be linked to each other")
        self.assertEqual(len(groups), 2, "There should only be 2 groups: (PO1,PO2) and (PO3,PO4)")

        # link non-linked PO to already linked PO
        po_5.alternative_po_ids |= po_4
        groups = self.env['purchase.order.group'].search([('order_ids', 'in', pos.ids)])
        self.assertEqual(len(po_3.alternative_po_ids), 3, "PO3 should now be linked to PO4 and PO5")
        self.assertEqual(len(po_4.alternative_po_ids), 3, "PO4 should now be linked to PO3 and PO5")
        self.assertEqual(len(po_5.alternative_po_ids), 3, "PO5 should now be linked to PO3 and PO4")
        self.assertEqual(len(groups), 2, "There should only be 2 groups: (PO1,PO2) and (PO3,PO4,PO5)")

        # link already linked PO to already linked PO
        po_5.alternative_po_ids |= po_1
        groups = self.env['purchase.order.group'].search([('order_ids', 'in', pos.ids)])
        self.assertEqual(len(po_1.alternative_po_ids), 5, "All 5 POs should be linked to each other now")
        self.assertEqual(len(groups), 1, "There should only be 1 group containing all 5 POs (other group should have auto-deleted")

        # remove all links, make sure group auto-deletes
        (pos - po_5).alternative_po_ids = [Command.clear()]
        groups = self.env['purchase.order.group'].search([('order_ids', 'in', pos.ids)])
        self.assertEqual(len(po_5.alternative_po_ids), 0, "Last PO should auto unlink from itself since group should have auto-deleted")
        self.assertEqual(len(groups), 0, "The group should have auto-deleted")

    def test_09_alternative_po_line_price_unit(self):
        """Checks PO line's `price_unit` is keep even if a line from an
        alternative is chosen and thus the PO line's quantity was set to 0. """
        # Creates a first Purchase Order.
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.res_partner_1
        with po_form.order_line.new() as line:
            line.product_id = self.product_09
            line.product_qty = 1
            line.price_unit = 16
        po_1 = po_form.save()

        # Creates an alternative PO.
        action = po_1.action_create_alternative()
        alt_po_wizard_form = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wizard_form.partner_id = self.res_partner_1
        alt_po_wizard_form.copy_products = True
        alt_po_wizard = alt_po_wizard_form.save()
        alt_po_wizard.action_create_alternative()

        # Set a lower price on the alternative and choses this PO line.
        po_2 = po_1.alternative_po_ids - po_1
        po_2.order_line.price_unit = 12
        po_2.order_line.action_choose()

        self.assertEqual(
            po_1.order_line.product_uom_qty, 0,
            "Line's quantity from the original PO should be reset to 0")
        self.assertEqual(
            po_1.order_line.price_unit, 16,
            "Line's unit price from the original PO shouldn't be changed")

    def test_10_alternative_po_line_price_unit_different_uom(self):
        """ Check that the uom is copied in the alternative PO, and the "unit_price"
        is calculated according to this uom and not that of the product """
        # Creates a first Purchase Order.
        po_form = Form(self.env['purchase.order'])
        self.product_09.standard_price = 10
        po_form.partner_id = self.res_partner_1
        with po_form.order_line.new() as line:
            line.product_id = self.product_09
            line.product_qty = 1
            line.product_uom = self.env.ref('uom.product_uom_dozen')
        po_1 = po_form.save()
        self.assertEqual(po_1.order_line[0].price_unit, 120)

        # Creates an alternative PO.
        action = po_1.action_create_alternative()
        alt_po_wizard_form = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wizard_form.partner_id = self.res_partner_1
        alt_po_wizard_form.copy_products = True
        alt_po_wizard = alt_po_wizard_form.save()
        alt_po_wizard.action_create_alternative()

        po_2 = po_1.alternative_po_ids - po_1
        self.assertEqual(po_2.order_line[0].product_uom, po_1.order_line[0].product_uom)
        self.assertEqual(po_2.order_line[0].price_unit, 120)
