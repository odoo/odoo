# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields

from odoo.tests import Form, tagged
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon


@tagged('post_install', '-at_install')
class TestSaleStockMargin(TestStockValuationCommon):

    @classmethod
    def setUpClass(cls):
        super(TestSaleStockMargin, cls).setUpClass()
        cls.pricelist = cls.env['product.pricelist'].create({'name': 'Simple Pricelist'})
        cls.env['res.currency.rate'].search([]).unlink()

    #########
    # UTILS #
    #########

    def _create_sale_order(self):
        return self.env['sale.order'].create({
            'name': 'Sale order',
            'partner_id': self.env.ref('base.partner_admin').id,
            'partner_invoice_id': self.env.ref('base.partner_admin').id,
            'pricelist_id': self.pricelist.id,
        })

    def _create_sale_order_line(self, sale_order, product, quantity, price_unit=0):
        return self.env['sale.order.line'].create({
            'name': 'Sale order',
            'order_id': sale_order.id,
            'price_unit': price_unit,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
        })

    def _create_product(self):
        product_template = self.env['product.template'].create({
            'name': 'Super product',
            'type': 'product',
        })
        product_template.categ_id.property_cost_method = 'fifo'
        return product_template.product_variant_ids

    #########
    # TESTS #
    #########

    def test_sale_stock_margin_1(self):
        sale_order = self._create_sale_order()
        product = self._create_product()

        self._make_in_move(product, 2, 35)
        self._make_out_move(product, 1)

        order_line = self._create_sale_order_line(sale_order, product, 1, 50)
        sale_order.action_confirm()

        self.assertEqual(order_line.purchase_price, 35)
        self.assertEqual(sale_order.margin, 15)

        sale_order.picking_ids.move_ids.quantity_done = 1
        sale_order.picking_ids.button_validate()

        self.assertEqual(order_line.purchase_price, 35)
        self.assertEqual(order_line.margin, 15)
        self.assertEqual(sale_order.margin, 15)

    def test_sale_stock_margin_2(self):
        sale_order = self._create_sale_order()
        product = self._create_product()

        self._make_in_move(product, 2, 32)
        self._make_in_move(product, 5, 17)
        self._make_out_move(product, 1)

        order_line = self._create_sale_order_line(sale_order, product, 2, 50)
        sale_order.action_confirm()

        self.assertEqual(order_line.purchase_price, 32)
        self.assertAlmostEqual(sale_order.margin, 36)

        sale_order.picking_ids.move_ids.quantity_done = 2
        sale_order.picking_ids.button_validate()

        self.assertAlmostEqual(order_line.purchase_price, 24.5)
        self.assertAlmostEqual(order_line.margin, 51)
        self.assertAlmostEqual(sale_order.margin, 51)

    def test_sale_stock_margin_3(self):
        sale_order = self._create_sale_order()
        product = self._create_product()

        self._make_in_move(product, 2, 10)
        self._make_out_move(product, 1)

        order_line = self._create_sale_order_line(sale_order, product, 2, 20)
        sale_order.action_confirm()

        self.assertEqual(order_line.purchase_price, 10)
        self.assertAlmostEqual(sale_order.margin, 20)

        sale_order.picking_ids.move_ids.quantity_done = 1
        sale_order.picking_ids.button_validate()

        self.assertAlmostEqual(order_line.purchase_price, 10)
        self.assertAlmostEqual(order_line.margin, 20)
        self.assertAlmostEqual(sale_order.margin, 20)

    def test_sale_stock_margin_4(self):
        sale_order = self._create_sale_order()
        product = self._create_product()

        self._make_in_move(product, 2, 10)
        self._make_in_move(product, 1, 20)
        self._make_out_move(product, 1)

        order_line = self._create_sale_order_line(sale_order, product, 2, 20)
        sale_order.action_confirm()

        self.assertEqual(order_line.purchase_price, 10)
        self.assertAlmostEqual(sale_order.margin, 20)

        sale_order.picking_ids.move_ids.quantity_done = 1
        res = sale_order.picking_ids.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        self.assertAlmostEqual(order_line.purchase_price, 15)
        self.assertAlmostEqual(order_line.margin, 10)
        self.assertAlmostEqual(sale_order.margin, 10)

    def test_sale_stock_margin_5(self):
        sale_order = self._create_sale_order()
        product_1 = self._create_product()
        product_2 = self._create_product()

        self._make_in_move(product_1, 2, 35)
        self._make_in_move(product_1, 1, 51)
        self._make_out_move(product_1, 1)

        self._make_in_move(product_2, 2, 17)
        self._make_in_move(product_2, 1, 11)
        self._make_out_move(product_2, 1)

        order_line_1 = self._create_sale_order_line(sale_order, product_1, 2, 60)
        order_line_2 = self._create_sale_order_line(sale_order, product_2, 4, 20)
        sale_order.action_confirm()

        self.assertAlmostEqual(order_line_1.purchase_price, 35)
        self.assertAlmostEqual(order_line_2.purchase_price, 17)
        self.assertAlmostEqual(order_line_1.margin, 25 * 2)
        self.assertAlmostEqual(order_line_2.margin, 3 * 4)
        self.assertAlmostEqual(sale_order.margin, 62)

        sale_order.picking_ids.move_ids[0].quantity_done = 2
        sale_order.picking_ids.move_ids[1].quantity_done = 3

        res = sale_order.picking_ids.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        self.assertAlmostEqual(order_line_1.purchase_price, 43)       # (35 + 51) / 2
        self.assertAlmostEqual(order_line_2.purchase_price, 12.5)     # (17 + 11 + 11 + 11) / 4
        self.assertAlmostEqual(order_line_1.margin, 34)               # (60 - 43) * 2
        self.assertAlmostEqual(order_line_2.margin, 30)               # (20 - 12.5) * 4
        self.assertAlmostEqual(sale_order.margin, 64)

    def test_sale_stock_margin_6(self):
        """ Test that the purchase price doesn't change when there is a service product in the SO"""
        service = self.env['product.product'].create({
            'name': 'Service',
            'type': 'service',
            'list_price': 100.0,
            'standard_price': 50.0})
        self.product1.list_price = 80.0
        self.product1.standard_price = 40.0
        sale_order = self._create_sale_order()
        order_line_1 = self._create_sale_order_line(sale_order, service, 1, 100)
        order_line_2 = self._create_sale_order_line(sale_order, self.product1, 1, 80)

        self.assertEqual(order_line_1.purchase_price, 50, "Sales order line cost should be 50.00")
        self.assertEqual(order_line_2.purchase_price, 40, "Sales order line cost should be 40.00")

        self.assertEqual(order_line_1.margin, 50, "Sales order line profit should be 50.00")
        self.assertEqual(order_line_2.margin, 40, "Sales order line profit should be 40.00")
        self.assertEqual(sale_order.margin, 90, "Sales order profit should be 90.00")

        # Change the purchase price of the service product.
        order_line_1.purchase_price = 100.0
        self.assertEqual(order_line_1.purchase_price, 100, "Sales order line cost should be 100.00")

        # Confirm the sales order.
        sale_order.action_confirm()

        self.assertEqual(order_line_1.purchase_price, 100, "Sales order line cost should be 100.00")
        self.assertEqual(order_line_2.purchase_price, 40, "Sales order line cost should be 40.00")

    def test_so_and_multicurrency(self):
        ResCurrencyRate = self.env['res.currency.rate']
        company_currency = self.env.company.currency_id
        other_currency = self.env.ref('base.EUR') if company_currency == self.env.ref('base.USD') else self.env.ref('base.USD')

        date = fields.Date.today()
        ResCurrencyRate.create({'currency_id': company_currency.id, 'rate': 1, 'name': date})
        other_currency_rate = ResCurrencyRate.search([('name', '=', date), ('currency_id', '=', other_currency.id)])
        if other_currency_rate:
            other_currency_rate.rate = 2
        else:
            ResCurrencyRate.create({'currency_id': other_currency.id, 'rate': 2, 'name': date})

        so = self._create_sale_order()
        so.pricelist_id = self.env['product.pricelist'].create({
            'name': 'Super Pricelist',
            'currency_id': other_currency.id,
        })

        product = self._create_product()
        product.standard_price = 100
        product.list_price = 200

        so_form = Form(so)
        with so_form.order_line.new() as line:
            line.product_id = product
        so = so_form.save()
        so_line = so.order_line

        self.assertEqual(so_line.purchase_price, 200)
        self.assertEqual(so_line.price_unit, 400)
        so.action_confirm()
        self.assertEqual(so_line.purchase_price, 200)
        self.assertEqual(so_line.price_unit, 400)

    def test_so_and_multicompany(self):
        """ In a multicompany environnement, when the user is on company C01 and confirms a SO that
        belongs to a second company C02, this test ensures that the computations will be based on
        C02's data"""
        main_company = self.env['res.company']._get_main_company()
        main_company_currency = main_company.currency_id
        new_company_currency = self.env.ref('base.EUR') if main_company_currency == self.env.ref('base.USD') else self.env.ref('base.USD')

        date = fields.Date.today()
        self.env['res.currency.rate'].create([
            {'currency_id': main_company_currency.id, 'rate': 1, 'name': date, 'company_id': False},
            {'currency_id': new_company_currency.id, 'rate': 3, 'name': date, 'company_id': False},
        ])

        new_company = self.env['res.company'].create({
            'name': 'Super Company',
            'currency_id': new_company_currency.id,
        })
        self.env.user.company_id = new_company.id

        self.pricelist.currency_id = new_company_currency.id

        product = self._create_product()

        incoming_picking_type = self.env['stock.picking.type'].search([('company_id', '=', new_company.id), ('code', '=', 'incoming')], limit=1)
        production_location = self.env['stock.location'].search([('company_id', '=', new_company.id), ('usage', '=', 'production')])

        picking = self.env['stock.picking'].create({
            'picking_type_id': incoming_picking_type.id,
            'location_id': production_location.id,
            'location_dest_id': incoming_picking_type.default_location_dest_id.id,
        })
        self.env['stock.move'].create({
            'name': 'Incoming Product',
            'product_id': product.id,
            'location_id': production_location.id,
            'location_dest_id': incoming_picking_type.default_location_dest_id.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 100,
            'picking_type_id': incoming_picking_type.id,
            'picking_id': picking.id,
        })
        picking.action_confirm()
        res_dict = picking.button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        wizard.process()

        self.pricelist.currency_id = new_company_currency.id
        partner = self.env['res.partner'].create({'name': 'Super Partner'})
        so = self.env['sale.order'].create({
            'name': 'Sale order',
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'pricelist_id': self.pricelist.id,
        })
        sol = self._create_sale_order_line(so, product, 1, price_unit=200)

        self.env.user.company_id = main_company.id
        so.action_confirm()

        self.assertEqual(sol.purchase_price, 100)
        self.assertEqual(sol.margin, 100)

    def test_purchase_price_changes(self):
        so = self._create_sale_order()
        product = self._create_product()
        product.categ_id.property_cost_method = 'standard'
        product.standard_price = 20
        self._create_sale_order_line(so, product, 1, product.list_price)

        so_form = Form(so)
        with so_form.order_line.edit(0) as line:
            line.purchase_price = 15
        so = so_form.save()
        email_act = so.action_quotation_send()
        email_ctx = email_act.get('context', {})
        so.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))

        self.assertEqual(so.state, 'sent')
        self.assertEqual(so.order_line[0].purchase_price, 15)

    def test_compute_average_price_with_different_company(self):
        """Ensure _compute_average_price correctly fetches price from the intended company context"""

        # Create Companies
        company_a = self.env['res.company'].create({'name': 'Company A'})
        company_b = self.env['res.company'].create({'name': 'Company B'})

        # Create Product Category with cost method other than 'standard'
        product_category = self.env['product.category'].with_company(company_b).create({
            'name': 'Test Category',
            'property_cost_method': 'average',
        })

        # Product for Company B
        main_product = self.env['product.product'].create({
            'name': 'Main Product',
            'type': 'product',
            'standard_price': 101.11,
            'company_id': company_b.id,
            'categ_id': product_category.id,
        })

        # Create additional product for the BOM
        product_b = self.env['product.product'].with_company(company_b).create({
            'name': 'Product B',
            'type': 'product',
            'standard_price': 100,
            'company_id': company_b.id,
            'categ_id': product_category.id,
        })

        # Create Bill of Materials (BoM) for the main product
        bom = self.env['mrp.bom'].with_company(company_b).create({
            'product_id': main_product.id,
            'product_tmpl_id': main_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': product_b.id, 'product_qty': 1})],
        })

        incoming_picking_type = self.env['stock.picking.type'].search([('company_id', '=', company_b.id), ('code', '=', 'incoming')], limit=1)
        production_location = self.env['stock.location'].search([('company_id', '=', company_b.id), ('usage', '=', 'production')])

        picking = self.env['stock.picking'].create({
            'picking_type_id': incoming_picking_type.id,
            'location_id': production_location.id,
            'location_dest_id': incoming_picking_type.default_location_dest_id.id,
        })

        # Create stock moves for Product B
        stock_moves = self.env['stock.move'].create([
            {
                'name': 'Move 1 - Product B',
                'product_id': product_b.id,
                'company_id': company_b.id,
                'product_uom_qty': 5,
                'product_uom': product_b.uom_id.id,
                'bom_line_id': bom.bom_line_ids[0].id,
                'location_id': production_location.id,
                'location_dest_id': incoming_picking_type.default_location_dest_id.id,
                'picking_type_id': incoming_picking_type.id,
                'picking_id': picking.id,
                'state': 'done',
            },
        ])

        # Create Sale Order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'company_id': company_b.id,
        })

        # Create Sale Order Line with main_product and link stock_moves
        sol = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': main_product.id,
            'product_uom_qty': 1,
            'product_uom': main_product.uom_id.id,
            'company_id': company_b.id,
            'move_ids': stock_moves.ids,
        })

        # Switch to Company A's context for the test
        self.env.company = company_a

        sol._compute_purchase_price()

        # Assert the computed price from Company A
        purchase_price_a = sol.product_id.with_company(company_a).standard_price
        self.assertEqual(purchase_price_a, 0, "Price be 0 as the product exists in Company B")

        # Assert that the computed price comes from Company B
        purchase_price = sol.purchase_price
        self.assertEqual(purchase_price, 100, "Price should be fetched from Company B, not Company A")
        self.assertNotEqual(purchase_price, 0, "Price should not be 0 as the product exists in Company B")
