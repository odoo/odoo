# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon
from odoo import Command, fields
from odoo.tests import Form

from datetime import timedelta

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
        line1 = (0, 0, {'product_id': self.product_09.id, 'product_qty': quantity, 'product_uom_id': self.product_uom_id.id, 'price_unit': price_product09})
        line2 = (0, 0, {'product_id': self.product_13.id, 'product_qty': quantity, 'product_uom_id': self.product_uom_id.id, 'price_unit': price_product13})

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
            'product_uom_id': product2.uom_id.id,
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
            line.product_uom_id = self.env.ref('uom.product_uom_dozen')
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
        self.assertEqual(orig_po.order_line[0].product_uom_id, alt_po_1.order_line[0].product_uom_id, "Alternative PO should have copied the product unit of measure from original PO")
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
        self.assertEqual(len(warning_wiz.alternative_po_ids), 1,
                         "POs not in a RFQ status should not be listed as possible to cancel")
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
            line.product_uom_id = self.env.ref('uom.product_uom_dozen')
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
        self.assertEqual(po_2.order_line[0].product_uom_id, po_1.order_line[0].product_uom_id)
        self.assertEqual(po_2.order_line[0].price_unit, 120)

    def test_11_alternative_po_from_po_with_requisition_id(self):
        """Create a purchase order from a blanket order, then check that the alternative purchase order
            can be created and that the requisition_id is not set on it.
        """
        # create an empty blanket order
        line1 = (0, 0, {
            'product_id': self.product_13.id,
            'product_uom_id': self.product_13.uom_id.id,
            'price_unit': 41,
            'product_qty': 10,
        })
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'requisition_type': 'blanket_order',
            'vendor_id': self.res_partner_1.id,
        })
        requisition_blanket.action_confirm()
        # lazy reproduction of clicking on "New Quotation" act_window button
        po_form = Form(self.env['purchase.order'].with_context({"default_requisition_id": requisition_blanket.id, "default_user_id": False}))
        po_1 = po_form.save()
        po_1.button_confirm()
        self.assertTrue(po_1.requisition_id, "The requisition_id should be set in the purchase order")

        # Creates an alternative PO.
        action = po_1.action_create_alternative()
        alt_po_wizard_form = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wizard_form.partner_id = self.res_partner_1
        alt_po_wizard_form.copy_products = True
        alt_po_wizard = alt_po_wizard_form.save()
        alt_po_wizard.action_create_alternative()

        po_2 = po_1.alternative_po_ids - po_1
        self.assertFalse(po_2.requisition_id, "The requisition_id should not be set in the alternative purchase order")

    def test_12_alternative_po_line_different_currency(self):
        """ Check alternative PO with different currency is compared correctly"""
        currency_eur = self.env.ref("base.EUR")
        currency_usd = self.env.ref("base.USD")
        (currency_usd | currency_eur).active = True

        self.env.ref('base.main_company').currency_id = currency_usd

        # 1 USD = 0.5 EUR
        self.env['res.currency.rate'].create([{
            'name': fields.Datetime.today(),
            'currency_id': self.env.ref('base.USD').id,
            'rate': 1,
        }, {
            'name': fields.Datetime.today(),
            'currency_id': self.env.ref('base.EUR').id,
            'rate': 0.5,
        }])
        vendor_usd = self.env["res.partner"].create({
            "name": "Supplier A",
        })
        vendor_eur = self.env["res.partner"].create({
            "name": "Supplier B",
        })

        product = self.env['product.product'].create({
            'name': 'Product',
            'seller_ids': [(0, 0, {
                'partner_id': vendor_usd.id,
                'price': 100,
                'currency_id': currency_usd.id,
            }), (0, 0, {
                'partner_id': vendor_eur.id,
                'price': 80,
                'currency_id': currency_eur.id,
            })]
        })
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = vendor_eur
        po_form.currency_id = currency_eur
        with po_form.order_line.new() as line:
            line.product_id = product
            line.product_qty = 1
        po_orig = po_form.save()
        self.assertEqual(po_orig.order_line.price_unit, 80)
        self.assertEqual(po_orig.currency_id, currency_eur)

        # Creates an alternative PO
        action = po_orig.action_create_alternative()
        alt_po_wizard_form = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wizard_form.partner_id = vendor_usd
        alt_po_wizard_form.copy_products = True
        alt_po_wizard = alt_po_wizard_form.save()
        alt_po_wizard.action_create_alternative()

        po_alt = po_orig.alternative_po_ids - po_orig
        # Ensure that the currency in the alternative purchase order is set to USD
        # because, in some case, the company's default currency is EUR.
        self.assertEqual(po_alt.currency_id, currency_usd)
        self.assertEqual(po_alt.order_line.price_unit, 100)

        # po_alt has cheaper price_unit/price_subtotal after conversion USD -> EUR
        # 80 / 0.5 = 160 USD > 100 EUR
        best_price_ids, best_date_ids, best_price_unit_ids = po_orig.get_tender_best_lines()
        self.assertEqual(len(best_price_ids), 1)
        # Equal dates
        self.assertEqual(len(best_date_ids), 2)
        self.assertEqual(len(best_price_unit_ids), 1)
        # alt_po is cheaper than orig_po
        self.assertEqual(best_price_ids[0], po_alt.order_line.id)
        self.assertEqual(best_price_unit_ids[0], po_alt.order_line.id)

    def test_alternative_po_with_multiple_price_list(self):
        vendor_a = self.env["res.partner"].create({
            "name": "Supplier A",
        })
        vendor_b = self.env["res.partner"].create({
            "name": "Supplier B",
        })
        product = self.env['product.product'].create({
            'name': 'Product',
            'seller_ids': [(0, 0, {
                'partner_id': vendor_a.id,
                'price': 5,
                'product_code': 'code A',
            }), (0, 0, {
                'partner_id': vendor_b.id,
                'price': 4,
                'min_qty': 10,
                'product_code': 'code B',
            }), (0, 0, {
                'partner_id': vendor_b.id,
                'price': 6,
                'min_qty': 1,
            }),
            ]
        })
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = vendor_a
        with po_form.order_line.new() as line:
            line.product_id = product
            line.product_qty = 100
        po_orig = po_form.save()
        self.assertEqual(po_orig.order_line.price_unit, 5)
        self.assertEqual(po_orig.order_line.name, '[code A] Product')
        # Creates an alternative PO
        action = po_orig.action_create_alternative()
        alt_po_wizard_form = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wizard_form.partner_id = vendor_b
        alt_po_wizard_form.copy_products = True
        alt_po_wizard = alt_po_wizard_form.save()
        alt_po_wizard.action_create_alternative()
        po_alt = po_orig.alternative_po_ids - po_orig
        self.assertEqual(po_alt.order_line.price_unit, 4)
        self.assertEqual(po_alt.order_line.name, '[code B] Product')

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
        line1 = Command.create({'product_id': self.product_09.id, 'product_uom_id': self.product_uom_id.id})
        line2 = Command.create({'product_id': self.product_13.id, 'product_uom_id': self.product_uom_id.id})

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

    def test_taxes_for_alternative_po(self):
        """
            Check that PO lines of PO generated by alternative compute taxes
        """
        product = self.product_13
        vendor = self.res_partner_1
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = vendor
        with po_form.order_line.new() as line:
            line.product_id = product
            line.product_qty = 1
        orig_po = po_form.save()
        # Creates an alternative PO
        action = orig_po.action_create_alternative()
        alt_po_wizard_form = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wizard_form.partner_id = vendor
        alt_po_wizard_form.copy_products = True
        alt_po_wizard = alt_po_wizard_form.save()
        alt_po_id = alt_po_wizard.action_create_alternative()['res_id']
        alt_po = self.env['purchase.order'].browse(alt_po_id)
        self.assertEqual(orig_po.order_line.taxes_id, alt_po.order_line.taxes_id)

    def test_alternative_purchase_order_merge(self):
        group_purchase_alternatives = self.env.ref('purchase_requisition.group_purchase_alternatives')
        self.env.user.write({'groups_id': [(4, group_purchase_alternatives.id, 0)]})
        po_1 = Form(self.env['purchase.order'])
        res_partner_2 = self.env['res.partner'].create({'name': 'Vendor 2'})
        res_partner_3 = self.env['res.partner'].create({'name': 'Vendor 3'})
        po_1.partner_id = self.res_partner_1
        with po_1.order_line.new() as po_line:
            po_line.product_id = self.product_09
            po_line.product_qty = 1
            po_line.price_unit = 100
        po_1 = po_1.save()

        action = po_1.action_create_alternative()
        alt_po_wiz = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wiz.partner_id = res_partner_2
        alt_po_wiz.copy_products = True
        alt_po_wiz = alt_po_wiz.save()
        alt_po_wiz.action_create_alternative()
        po_2 = Form(self.env['purchase.order'])
        po_2.partner_id = res_partner_3
        with po_2.order_line.new() as po_line_1:
            po_line_1.product_id = self.product_09
            po_line_1.product_qty = 5
            po_line_1.price_unit = 100
        po_2 = po_2.save()

        action = po_2.action_create_alternative()
        alt_po_wiz = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wiz.partner_id = res_partner_2
        alt_po_wiz.copy_products = True
        alt_po_wiz = alt_po_wiz.save()
        alt_po_wiz.action_create_alternative()
        po_orders = self.env['purchase.order'].search([('partner_id', '=', res_partner_2.id)])
        merger_alternative_orders = po_orders[0] | po_orders[1]
        merger_alternative_orders.action_merge()
        self.assertEqual(len(po_orders[0].alternative_po_ids), 4)
