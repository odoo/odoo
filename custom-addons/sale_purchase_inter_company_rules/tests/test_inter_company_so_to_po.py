# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestInterCompanyRulesCommonSOPO
from odoo import Command
from odoo.tests import Form
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestInterCompanySaleToPurchase(TestInterCompanyRulesCommonSOPO):

    def _generate_draft_sale_order(self, company, partner, user):
        """ Generate sale order and confirm its state """
        sale_order = Form(self.env['sale.order'])
        sale_order.company_id = company
        sale_order.warehouse_id = company.warehouse_id
        sale_order.partner_id = partner
        sale_order.user_id = user
        with sale_order.order_line.new() as line:
            line.name = 'Service'
            line.product_id = self.product_consultant
            line.price_unit = 450.0

        return sale_order.save()

    def generate_sale_order(self, company, partner, user):
        sale_order = self._generate_draft_sale_order(company, partner, user)
        sale_order.action_confirm()

    def validate_generated_purchase_order(self, company, partner):
        """ Validate purchase order which has been generated from sale order
        and test its state, total_amount, product_name and product_quantity.
        """

        # I check that Quotation of purchase order and order line is same as sale order
        purchase_order = self.env['purchase.order'].search([('company_id', '=', partner.id)], limit=1)

        self.assertEqual(purchase_order.state, "draft", "Invoice should be in draft state.")
        self.assertEqual(purchase_order.partner_id, company.partner_id, "Vendor does not correspond to Company %s." % company.name)
        self.assertEqual(purchase_order.company_id, partner, "Company is not correspond to purchase order.")
        self.assertEqual(purchase_order.amount_total, 517.5, "Total amount is incorrect.")
        self.assertEqual(purchase_order.order_line[0].product_id, self.product_consultant, "Product in line is incorrect.")
        self.assertEqual(purchase_order.order_line[0].name, 'Service', "Product name is incorrect.")
        self.assertEqual(purchase_order.order_line[0].price_unit, 450, "Price unit is incorrect.")
        self.assertEqual(purchase_order.order_line[0].product_qty, 1, "Product qty is incorrect.")
        self.assertEqual(purchase_order.order_line[0].price_subtotal, 450, "line total is incorrect.")
        return purchase_order

    def test_00_inter_company_sale_purchase(self):
        """ Configure "Sale/Purchase" option and then Create sale order and find related
        purchase order to related company and compare them.
        """

        # Generate sale order in company A for company B
        self.company_b.update({
            'rule_type': 'sale_purchase',
        })
        self.generate_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        # Check purchase order is created in company B ( for company A )
        self.validate_generated_purchase_order(self.company_a, self.company_b)
        # reset configuration of company B
        self.company_b.update({
            'rule_type': False,
        })

        # Generate sale order in company B for company A
        self.company_a.update({
            'rule_type': 'sale_purchase',
        })
        self.generate_sale_order(self.company_b, self.company_a.partner_id, self.res_users_company_b)
        # Check purchase order is created in company A ( for company B )
        self.validate_generated_purchase_order(self.company_b, self.company_a)
        # reset configuration of company A
        self.company_a.update({
            'rule_type': False,
        })

    def test_01_inter_company_sale_order_with_configuration(self):
        """ Configure only "Sale" option and then Create sale order and find related
        purchase order to related company and compare them.
        """

        # Generate sale order in company A for company B
        self.company_b.update({
            'rule_type': 'sale',
        })
        self.generate_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        # Check purchase order is created in company B ( for company A )
        self.validate_generated_purchase_order(self.company_a, self.company_b)
        # reset configuration of company B
        self.company_b.update({
            'rule_type': False,
        })

        # Generate sale order in company B for company A
        self.company_a.update({
            'rule_type': 'sale',
        })
        self.generate_sale_order(self.company_b, self.company_a.partner_id, self.res_users_company_b)
        # Check purchase order is created in company A ( for company B )
        self.validate_generated_purchase_order(self.company_b, self.company_a)
        # reset configuration of company A
        self.company_a.update({
            'rule_type': False,
        })

    def test_02_sale_to_purchase_without_configuration(self):
        """ Without any Configuration Create sale order and try to find related
        purchase order to related company.
        """

        # Generate sale order in company A for company B
        self.generate_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        # I check that purchase order has been created with company_b
        purchase_order = self.env['purchase.order'].search([('company_id', '=', self.company_b.id)], limit=1)
        self.assertTrue((not purchase_order), "Purchase order created for company A from Purchase order of company B without configuration")

        # Generate sale order in company A for company B
        self.generate_sale_order(self.company_b, self.company_a.partner_id, self.res_users_company_b)
        # I check that purchase order has been created with company_a
        purchase_order = self.env['purchase.order'].search([('company_id', '=', self.company_a.id)], limit=1)
        self.assertTrue((not purchase_order), "Sale order created for company B from Purchase order of company B without configuration")

    def test_03_inter_company_so_section(self):
        """ Configure "Sale/Purchase" option.
        Create a sale order which has a section line
        Find related purchase order to related company and compare them.
        """

        # Generate sale order in company A for company B
        self.company_b.update({
            'rule_type': 'sale_purchase',
        })
        so = self._generate_draft_sale_order(self.company_a, self.company_b.partner_id, self.res_users_company_a)
        so.write({
            'order_line': [(0, False, {'display_type': 'line_section', 'name': 'Great Section'})]
        })
        so.action_confirm()
        self.assertEqual(len(so.order_line), 2)
        # Check purchase order is created in company B ( for company A )
        po = self.validate_generated_purchase_order(self.company_a, self.company_b)
        self.assertEqual(len(po.order_line), 2)

    def test_04_inter_company_auto_validation(self):
        """ Configure "Sale/Purchase" option and tick auto validation.
        Find related purchase order to related company and confirm it.
        """
        # Create a product in 'Auto Purchase' to by in company B
        my_service = self.env['product.product'].create({
            'name': 'my service',
            'type': 'service',
            'service_to_purchase': True,
            'seller_ids': [(0, 0, {'partner_id': self.company_b.partner_id.id, 'price': 100, 'company_id': self.company_a.id})]
        })

        self.company_b.update({
            'rule_type': 'sale_purchase',
            'auto_validation': True,
        })
        # Generate sale order in company A for company B
        partner_a = self.env['res.partner'].create({
            'name': 'partner_a',
            'company_id': False,
        })
        so = self._generate_draft_sale_order(self.company_a, partner_a, self.res_users_company_a)
        so.order_line.product_id = my_service
        so.order_line.product_uom = my_service.uom_id
        so.with_user(self.res_users_company_a).action_confirm()
        # Check purchase order is created in company B ( for company A )
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.company_b.partner_id.id)], limit=1)
        self.assertTrue(purchase_order)
        purchase_order.with_user(self.res_users_company_a).button_confirm()

    def test_sale_to_specific_partner(self):
        """
        Classic intercompany SO-PO on company C2. C1 sells to a child of C2. It
        should still create a PO on C2 side.
        """
        self.company_b.rule_type = 'sale_purchase'
        partner_b = self.env['res.partner'].create({
            'name': 'SuperPartner',
            'parent_id': self.company_b.partner_id.id,
        })
        so = self._generate_draft_sale_order(self.company_a, partner_b, self.res_users_company_a)
        so.with_user(self.res_users_company_a).action_confirm()
        purchase_order = self.env['purchase.order'].sudo().search([('partner_id', '=', self.company_a.partner_id.id)], limit=1)
        self.assertEqual(purchase_order.company_id, self.company_b)

    def test_inter_company_auto_validation(self):
        """
        In a setup with two companies A and B, with a service product that is set as a "Subcontract Services".
        Company A purchase the service from company B, and company B purchase the service from a vendor.
        We test that if we make a purchase order on A and confirm it that it generate an SO in B and a PO.
        """
        buyer, vendor = self.env['res.partner'].create([{
            'name': 'buyer',
            'company_id': False,
        }, {
            'name': 'vendor',
            'company_id': False,
        }])

        (self.company_a | self.company_b).update({
            'rule_type': 'sale_purchase',
            'auto_validation': True,
        })

        service_purchase = self.env['product.product'].create({
            'name': "service 1",
            'purchase_ok': True,
            'sale_ok': True,
            'type': 'service',
            'service_to_purchase': True,
            'seller_ids': [
                Command.create({'partner_id': self.company_b.partner_id.id, 'price': 100, 'company_id': self.company_a.id}),
                Command.create({'partner_id': vendor.id, 'price': 100, 'company_id': self.company_b.id}),
            ],
        })
        service_purchase.with_company(self.company_b).update({'service_to_purchase': True})

        so_a = self._generate_draft_sale_order(self.company_a, buyer, self.res_users_company_a)
        so_a.order_line.product_id = service_purchase
        so_a.with_company(self.company_a).action_confirm()

        po_a = so_a._get_purchase_orders()
        self.assertEqual(po_a.company_id, self.company_a)
        self.assertEqual(po_a.partner_id, self.company_b.partner_id)
        self.assertEqual(po_a.order_line.product_id, service_purchase)

        po_a.with_company(self.company_a).button_approve()
        so_b = self.env['sale.order'].with_company(self.company_b).search([('partner_id', '=', self.company_a.partner_id.id)], limit=1)
        self.assertEqual(so_b.company_id, self.company_b)
        self.assertEqual(so_b.partner_id, self.company_a.partner_id)
        self.assertEqual(so_b.order_line.product_id, service_purchase)

        po_b = so_b._get_purchase_orders()
        self.assertEqual(po_b.company_id, self.company_b)
        self.assertEqual(po_b.partner_id, vendor)
        self.assertEqual(po_b.order_line.product_id, service_purchase)

    def test_inter_company_putaway_rules(self):
        """
        Check that putaway strategies are correctly applied on tracked products
        when the transaction is updated by an intercompany procedure.
        """
        # with company A:
        self.company_a.update({
            'rule_type': 'sale_purchase',
            'auto_validation': True,
            'copy_lots_delivery': True,
        })
        stock_location_a = self.env['stock.warehouse'].search([('company_id', '=', self.company_a.id)], limit=1).lot_stock_id
        shelf_location = self.env['stock.location'].with_company(self.company_a).create({
            'name': 'Shelf',
            'usage': 'internal',
            'location_id': stock_location_a.id,
        })
        self.env["stock.putaway.rule"].with_company(self.company_a).create({
            "location_in_id": stock_location_a.id,
            "location_out_id": shelf_location.id,
            'category_id': self.env.ref('product.product_category_all').id,
        })
        # with company B:
        my_product = self.env['product.product'].with_company(self.company_b).create({
            'name': 'my product',
            'type': 'product',
            'tracking': 'serial',
            'sale_ok': True,
        })
        my_lot = self.env['stock.lot'].with_company(self.company_b).create({
            'name': 'SN0001',
            'product_id': my_product.id,
        })
        stock_location_b = self.env['stock.warehouse'].search([('company_id', '=', self.company_b.id)], limit=1).lot_stock_id
        self.env['stock.quant'].with_company(self.company_b)._update_available_quantity(my_product, stock_location_b, 1, lot_id=my_lot)
        so = self.env['sale.order'].with_company(self.company_b).create({
                'partner_id': self.company_a.partner_id.id,
                'order_line': [Command.create({
                        'product_id': my_product.id,
                        'price_unit': 100,
                    })
                ]
        })
        so.action_confirm()
        # Check that the stock move line linked to the purchase order created
        # and confirmed for company A (by company B) applied the putaway rule
        po = self.env['purchase.order'].search([('auto_sale_order_id', '=', so.id)], limit=1)
        picking_destination = po.picking_ids.move_line_ids.location_dest_id
        self.assertEqual(picking_destination, shelf_location)
        self.assertFalse(po.picking_ids.move_line_ids.lot_id)
        # Confirm the delivery created in company B to update the delivery in Company A
        delivery_b = so.picking_ids
        delivery_b.move_line_ids.lot_id = my_lot
        delivery_b.button_validate()
        receipt_a = po.picking_ids
        self.assertEqual(receipt_a.move_line_ids.location_dest_id, shelf_location)
        receipt_a.button_validate()
        self.assertEqual(receipt_a.move_line_ids.location_dest_id, shelf_location)
        self.assertEqual(receipt_a.move_line_ids.lot_id.name, my_lot.name)
        self.assertTrue(receipt_a.move_line_ids.picked)
