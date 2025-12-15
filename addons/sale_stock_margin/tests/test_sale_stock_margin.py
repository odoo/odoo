# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time

from odoo import fields
from odoo.tests import Form, tagged
from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged('post_install', '-at_install')
class TestSaleStockMargin(TestStockValuationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Simple Pricelist',
            'company_id': False,
        })
        cls.env['res.currency.rate'].search([]).unlink()
        cls.customer = cls.env['res.partner'].create({
            'name': 'Customer',
        })

    #########
    # UTILS #
    #########

    def _create_sale_order(self):
        return self.env['sale.order'].create({
            'name': 'Sale order',
            'partner_id': self.customer.id,
            'partner_invoice_id': self.customer.id,
            'pricelist_id': self.pricelist.id,
        })

    def _create_sale_order_line(self, sale_order, product, quantity, price_unit=0):
        return self.env['sale.order.line'].create({
            'name': 'Sale order',
            'order_id': sale_order.id,
            'price_unit': price_unit,
            'product_id': product.id,
            'product_uom_qty': quantity,
        })

    def _create_product(self):
        product_template = self.env['product.template'].create({
            'name': 'Super product',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        product_template.categ_id.property_cost_method = 'fifo'
        return product_template.product_variant_ids

    def _setup_multicurrency(self):
        usd = self.env.ref('base.USD')
        self.company_currency = self.env.company.currency_id
        self.other_currency = self.env.ref('base.EUR') if self.company_currency == usd else usd
        date = fields.Date.today()
        self.env['res.currency.rate'].create([
            {'currency_id': self.company_currency.id, 'rate': 1, 'name': date},
            {'currency_id': self.other_currency.id, 'rate': 2, 'name': date},
        ])
        return self.company_currency, self.other_currency

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

        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
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

        self.assertEqual(order_line.purchase_price, 19.5)
        self.assertAlmostEqual(sale_order.margin, 61)

        sale_order.picking_ids.move_ids.write({'quantity': 2, 'picked': True})
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

        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
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

        self.assertEqual(order_line.purchase_price, 15)
        self.assertAlmostEqual(sale_order.margin, 10)

        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

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

        self.assertAlmostEqual(order_line_1.purchase_price, 43)
        self.assertAlmostEqual(order_line_2.purchase_price, 14)
        self.assertAlmostEqual(order_line_1.margin, 17 * 2)
        self.assertAlmostEqual(order_line_2.margin, 6 * 4)
        self.assertAlmostEqual(sale_order.margin, 58)

        sale_order.picking_ids.move_ids[0].write({'quantity': 2, 'picked': True})
        sale_order.picking_ids.move_ids[1].write({'quantity': 3, 'picked': True})

        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        self.assertAlmostEqual(order_line_1.purchase_price, 43)       # (35 + 51) / 2
        self.assertAlmostEqual(order_line_2.purchase_price, 12.5)     # (17 + 11 + 11 + 11) / 4
        self.assertAlmostEqual(order_line_1.margin, 34)               # (60 - 43) * 2
        self.assertAlmostEqual(order_line_2.margin, 30)               # (20 - 12.5) * 4
        self.assertAlmostEqual(sale_order.margin, 64)

    def test_sale_stock_margin_6(self):
        """ Test that the purchase price doesn't change when there is a service product in the SO"""
        product = self.product_standard
        service = self.env['product.product'].create({
            'name': 'Service',
            'type': 'service',
            'list_price': 100.0,
            'standard_price': 50.0})
        product.list_price = 80.0
        product.standard_price = 40.0
        sale_order = self._create_sale_order()
        order_line_1 = self._create_sale_order_line(sale_order, service, 1, 100)
        order_line_2 = self._create_sale_order_line(sale_order, product, 1, 80)

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
        _company_currency, other_currency = self._setup_multicurrency()
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
        product.categ_id.property_cost_method = 'fifo'
        product.standard_price = 100

        incoming_picking_type = self.env['stock.picking.type'].search([('company_id', '=', new_company.id), ('code', '=', 'incoming')], limit=1)
        production_location = self.env['stock.location'].search([('company_id', '=', new_company.id), ('usage', '=', 'production')])

        picking = self.env['stock.picking'].create({
            'picking_type_id': incoming_picking_type.id,
            'location_id': production_location.id,
            'location_dest_id': incoming_picking_type.default_location_dest_id.id,
        })
        self.env['stock.move'].create({
            'product_id': product.id,
            'location_id': production_location.id,
            'location_dest_id': incoming_picking_type.default_location_dest_id.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1,
            'picking_type_id': incoming_picking_type.id,
            'picking_id': picking.id,
        })
        picking.action_confirm()
        picking.button_validate()
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
        self._setup_multicurrency()
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
        so.with_context(**email_ctx).message_post_with_source(
            self.env['mail.template'].browse(email_ctx.get('default_template_id')),
            subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
        )

        self.assertEqual(so.state, 'sent')
        self.assertEqual(so.order_line[0].purchase_price, 15)
        so.action_confirm()
        self.assertEqual(so.order_line[0].purchase_price, 15)

        # Set SO back to draft, and trigger purchase price recompute via currency change
        so.with_context(disable_cancel_warning=True).action_cancel()
        so.action_draft()
        so.currency_id = self.other_currency
        self.assertEqual(so.order_line.move_ids.state, 'cancel')
        self.assertEqual(so.order_line.purchase_price, 40)

    def test_add_product_on_delivery_price_unit_on_sale(self):
        """ Adding a product directly on a sale order's delivery should result in the new SOL
        having its `purchase_price` and `margin` + `margin_percent` fields correctly calculated.
        """
        products = [self._create_product() for _ in range(2)]
        for product, cost, price in zip(products, [20, 10], [25, 20]):
            product.categ_id.property_cost_method = 'standard'
            product.write({
                'standard_price': cost,
                'list_price': price,
                'invoice_policy': 'delivery',
            })
        sale_order = self._create_sale_order()
        self._create_sale_order_line(sale_order, products[0], 10, products[0].list_price)
        sale_order.action_confirm()
        delivery = sale_order.picking_ids[0]
        with Form(delivery) as delivery_form:
            with delivery_form.move_ids.new() as move:
                move.product_id = products[1]
                move.product_uom_qty = 10
        delivery.move_ids.quantity = 10
        delivery.button_validate()
        self.assertRecordValues(
            sale_order.order_line.filtered(lambda sol: sol.product_id == products[1]),
            [{
                'price_unit': products[1].list_price,
                'purchase_price': products[1].standard_price,
                'margin': 100,
                'margin_percent': 0.5,
            }]
        )

    def test_add_standard_product_on_delivery_cost_on_sale_order(self):
        """ test that if product with standard cost method is added in delivery, the cost is computed."""
        product = self.product_standard
        product.write({
                'standard_price': 20,
                'list_price': 25,
                'invoice_policy': 'order',
            })
        product2 = self.env['product.product'].create({
            'name': 'product2',
            'type': 'consu',
            'is_storable': True,
            'standard_price': 10,
            'list_price': 20,
            'invoice_policy': 'order',
        })
        sale_order = self._create_sale_order()
        self._create_sale_order_line(sale_order, product, 10, product.list_price)
        sale_order.action_confirm()
        delivery = sale_order.picking_ids[0]
        with Form(delivery) as delivery_form:
            with delivery_form.move_ids.new() as move:
                move.product_id = product2
                move.product_uom_qty = 10
        delivery.move_ids.quantity = 10
        delivery.button_validate()
        self.assertEqual(sale_order.order_line.filtered(lambda sol: sol.product_id == product2).purchase_price, 10)

    def test_add_avco_product_on_delivery_cost_on_sale_order(self):
        """ test that if product with avco cost method and an order "invoice_policy" is added in delivery, the cost is computed."""
        categ_average = self.env['product.category'].create({
            'name': 'AVERAGE',
            'property_cost_method': 'average'
        })
        self.product = self.product_avco
        self.product.write({
                'standard_price': 20,
                'list_price': 25,
                'invoice_policy': 'order',
            })
        product2 = self.env['product.product'].create({
            'name': 'product2',
            'type': 'consu',
            'is_storable': True,
            'categ_id': categ_average.id,
            'standard_price': 10,
            'list_price': 20,
            'invoice_policy': 'order',
        })
        sale_order = self._create_sale_order()
        self._create_sale_order_line(sale_order, self.product, 10, self.product.list_price)
        sale_order.action_confirm()
        delivery = sale_order.picking_ids[0]
        with Form(delivery) as delivery_form:
            with delivery_form.move_ids.new() as move:
                move.product_id = product2
                move.product_uom_qty = 10
        delivery.move_ids.quantity = 10
        delivery.button_validate()
        self.assertEqual(sale_order.order_line.filtered(lambda sol: sol.product_id == product2).purchase_price, 10)

    def test_avco_does_not_mix_products_on_compute_avg_price(self):
        """
        Ensure that when stock moves are duplicated and their product changed,
        the sale line linkage is cleared correctly, preventing average price
        computation from mixing valuation layers of different products.
        This test verifies that:
        - The duplicated delivery's moves lose the original sale_line_id when the product changes.
        - A new sale order line is created for the new product, increasing the total order lines.
        - Validations of deliveries and return pickings proceed without errors.
        - The purchase price on the original sale line remains accurate (unchanged).
        """
        self.product_avco_auto.uom_id = self.env.ref('uom.product_uom_dozen').id
        sale_order = self._create_sale_order()
        sale_order_line = self._create_sale_order_line(sale_order, self.product_avco, 1)
        sale_order.action_confirm()

        first_delivery = sale_order.picking_ids
        second_delivery = first_delivery.copy()
        self.assertEqual(second_delivery.move_ids.sale_line_id, sale_order_line)
        second_delivery.move_ids.product_id = self.product_avco_auto
        self.assertFalse(second_delivery.move_ids.sale_line_id)
        self.assertTrue(len(sale_order.order_line), 2)
        second_delivery.action_confirm()
        second_delivery.move_ids.quantity = 1
        second_delivery.button_validate()
        self.assertEqual(second_delivery.move_ids.sale_line_id, sale_order.order_line - sale_order_line)
        stock_picking_return = self.env['stock.return.picking'].create({
            'picking_id': second_delivery.id,
        })
        stock_picking_return.product_return_moves.quantity = 1
        return_picking = stock_picking_return._create_return()
        return_picking.move_ids.quantity = 1
        return_picking.button_validate()
        self.assertEqual(return_picking.state, 'done')

        first_delivery.move_ids.quantity = 1
        first_delivery.button_validate()
        self.assertEqual(first_delivery.state, 'done')
        self.assertEqual(sale_order_line.purchase_price, 10)

    def test_avco_different_uom(self):
        pack_of_6 = self.ref('uom.product_uom_pack_6')
        self.product_avco.write({
                'standard_price': 1,
                'list_price': 3,
                'uom_ids': [pack_of_6],
            })
        sale_order = self._create_sale_order()
        sale_order_line = self.env['sale.order.line'].create({
            'name': 'Sale order',
            'order_id': sale_order.id,
            'product_id': self.product_avco.id,
            'product_uom_qty': 1,
            'product_uom_id': pack_of_6,
        })
        sale_order.action_confirm()
        self.assertEqual(sale_order_line.margin, 12.0)

    def test_avco_calc(self):
        """ test purchase_price and margin correct calculation for avco product"""
        # need to freezetime due to test being too fast resulting in inconsistent AVCO calculation for in/out moves having the same exact validation date
        with freeze_time() as freeze:
            so = self._create_sale_order()
            self.product_avco_auto.list_price = 100
            self._make_in_move(self.product_avco_auto, 2, 20)
            self._make_in_move(self.product_avco_auto, 2, 40)
            self.assertEqual(self.product_avco_auto.standard_price, 30, "standard_price for avco = (2 * 20 + 2 * 40) / (2 + 2) = 30: 4 in stock")
            freeze.tick(delta=datetime.timedelta(seconds=2))

            # SOL quantity=2, qty_delivered=0
            sol = self._create_sale_order_line(so, self.product_avco_auto, 2, 100)
            self.assertEqual(sol.product_uom_qty, 2)
            self.assertEqual(sol.qty_delivered, 0)
            self.assertEqual(sol.purchase_price, 30, "purchase_price should match product's standard_price")
            self.assertEqual(sol.margin, 140, "margin = (sale price - purchase_price) * SOL quantity = (100 - 30) * 2 = 140")

            # SOL quantity=2, qty_delivered=1
            so.action_confirm()
            move = sol.move_ids
            move.quantity = 1
            delivery = move.picking_id
            backorder_wizard_values = delivery.button_validate()
            backorder_wizard = self.env[(backorder_wizard_values.get('res_model'))].browse(backorder_wizard_values.get('res_id')).with_context(backorder_wizard_values['context'])
            backorder_wizard.process()
            # purchase_unit_from_delivery = line.move_ids(done)._get_price_unit = (1 * 30) / (1) = 30
            # qty_from_std_price = max(SOL quantity - qty_from_delivery, 0) = 2 - 1 = 1
            self.assertEqual(sol.purchase_price, 30, "purchase_price = (qty_delivered * purchase_unit_from_delivery + qty_from_std_price * standard_price)/(qty_from_delivery + qty_from_std_price) = (1 * 30 + 1 * 30)/ (1 + 1) = 30")
            self.assertEqual(sol.margin, 140, "margin = (sale price - purchase_price) * SOL quantity = (100 - 30) * 2 = 140")
            freeze.tick(delta=datetime.timedelta(seconds=2))

            # SOL quantity=2, qty_delivered=3
            self._make_in_move(self.product_avco_auto, 2, 142.5)
            self.assertEqual(self.product_avco_auto.standard_price, 75, "standard_price for avco = (3 * 30 + 2 * 142.5) / (3 + 2) = 75: 3 remaining + 2 added to stock")
            self.assertEqual(sol.purchase_price, 30, "purchase_price shouldn't have changed")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            move = sol.move_ids.filtered(lambda m: m.state != 'done')
            move.quantity = 2
            delivery = move.picking_id
            delivery.button_validate()
            # purchase_unit_from_delivery = line.move_ids(done)._get_price_unit = (1 * 30 + 2 * 75) / (1 + 2) = 60
            # qty_from_std_price = max(SOL quantity - qty_from_delivery, 0) = max(2 - 3, 0) = 0
            self.assertEqual(sol.purchase_price, 60, "purchase_price = (qty_delivered * purchase_unit_from_delivery + qty_from_std_price * standard_price)/(qty_from_delivery + qty_from_std_price) = (3 * 60 + 0 * 75)/ (3 + 0) = 60")
            self.assertEqual(sol.margin, 80, "margin = (sale price - purchase_price) * SOL quantity = (100 - 60) * 2 = 80")

    def test_avco_zero_quantity(self):
        """ test that the purchase_price and margin are still calculated correctly when 0 quantity SOL
        including when a return is done for avco valuated product"""
        # need to freezetime due to test being too fast resulting in inconsistent AVCO calculation for in/out moves having the same exact validation date
        with freeze_time() as freeze:
            so = self._create_sale_order()
            self.product_avco_auto.list_price = 100
            self._make_in_move(self.product_avco_auto, 2, 20)
            self._make_in_move(self.product_avco_auto, 2, 40)
            self.assertEqual(self.product_avco_auto.standard_price, 30, "standard_price for avco = (2 * 20 + 2 * 40) / (2 + 2) = 30: 4 in stock")
            sol = self._create_sale_order_line(so, self.product_avco_auto, 1, 100)
            # SOL quantity=1, qty_delivered=0
            self.assertEqual(sol.product_uom_qty, 1)
            self.assertEqual(sol.qty_delivered, 0)
            self.assertEqual(sol.purchase_price, self.product_avco_auto.standard_price, "purchase_price should match product's standard_price")
            self.assertEqual(sol.margin, 70, "margin = (sale price - purchase_price) * SOL quantity = (100 - 30) * 1 = 70")
            so.action_confirm()

            # SOL quantity=0, qty_delivered=0
            sol2 = self._create_sale_order_line(so, self.product_avco_auto, 0, 90)
            self.assertEqual(sol2.product_uom_qty, 0)
            self.assertEqual(sol2.qty_delivered, 0)
            self.assertEqual(sol2.purchase_price, self.product_avco_auto.standard_price, "0 Quantity and 0 Delivered => default to standard price")
            self.assertEqual(sol2.margin, 0, "margin = 0 if no quantities sold/delivered")

            # SOL quantity=1, qty_delivered=1
            self._make_in_move(self.product_avco_auto, 2, 60)
            self.assertEqual(self.product_avco_auto.standard_price, 40, "standard_price for avco = (4 * 30 + 2 * 60) / (4 + 2) = 40: 4 existing + 2 added to stock")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            move = sol.move_ids
            move.quantity = sol.product_uom_qty
            delivery = move.picking_id
            delivery.button_validate()
            self.assertEqual(sol.product_uom_qty, 1)
            self.assertEqual(sol.qty_delivered, 1)
            self.assertEqual(sol.purchase_price, self.product_avco_auto.standard_price, "purchase_price should match product's standard_price")
            self.assertEqual(sol.margin, 60, "margin = (sale price - purchase_price) * SOL quantity = (100 - 40) * 1 = 60")
            freeze.tick(delta=datetime.timedelta(seconds=2))

            # SOL quantity=1, qty_delivered=-2
            self._make_in_move(self.product_avco_auto, 2, 5)
            self.assertEqual(self.product_avco_auto.standard_price, 30, "standard_price for avco = (5 * 40 + 2 * 5) / (5 + 2) = 30: 1 delivered, 5 remaining + 2 added to stock")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(active_id=delivery.id, active_model='stock.picking'))
            stock_return_picking = stock_return_picking_form.save()
            stock_return_picking.product_return_moves.quantity = 3.0
            stock_return_picking_action = stock_return_picking.action_create_returns()
            return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
            return_pick.button_validate()
            self.assertEqual(sol.product_uom_qty, 1)
            self.assertEqual(sol.qty_delivered, -2)
            self.assertEqual(self.product_avco_auto.standard_price, 33, "standard_price for avco = (7 * 30 + 3 * 40) / (7 + 3)) = 33: 7 remaining + 3 returned")
            self.assertEqual(sol.purchase_price, self.product_avco_auto.standard_price, "< 0 Delivered => default to standard price")
            self.assertEqual(sol.margin, 67, "margin = (sale price - purchase_price) * SOL quantity = (100 - 33) * 1 = 67")
            freeze.tick(delta=datetime.timedelta(seconds=2))

            # SOL quantity=0, qty_delivered=-2
            self._make_in_move(self.product_avco_auto, 2, 30)
            self.assertEqual(self.product_avco_auto.standard_price, 32.5, "standard_price for avco = (10 * 33 + 2 * 30) / 12 = 32.5: 10 remaining + 2 added to stock")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            sol.product_uom_qty = 0
            self.assertEqual(sol.purchase_price, self.product_avco_auto.standard_price, "< 0 Delivered => default to standard price")
            self.assertEqual(sol.margin, -135, "margin = (sale price - purchase_price) * qty_delivered = (100 - 32.5) * -2 = -135")

            # SOL quantity=0, qty_delivered=2
            so2 = self._create_sale_order()
            # throwaway product so we can deliver extra product in delivery
            throwaway_sol = self._create_sale_order_line(so2, self.product_standard, 1, 100)
            so2.action_confirm()
            move = throwaway_sol.move_ids
            move.quantity = throwaway_sol.product_uom_qty
            delivery = move.picking_id
            with Form(delivery) as delivery_form:
                with delivery_form.move_ids.new() as extra_move:
                    extra_move.product_id = self.product_avco_auto
                    extra_move.quantity = 2
            delivery.button_validate()
            sol3 = so2.order_line - throwaway_sol
            self.assertEqual(sol3.product_uom_qty, 0)
            self.assertEqual(sol3.qty_delivered, 2)
            self.assertEqual(self.product_avco_auto.standard_price, 32.5, 'no new incoming moves, std price should be unchanged')
            # purchase_unit_from_delivery = line.move_ids(done)._get_price_unit = (2 * 32.5) / 2 = 32.5
            self.assertEqual(sol3.purchase_price, self.product_avco_auto.standard_price, "purchase_price should match product's standard_price")
            self.assertEqual(sol3.margin, -65, "margin = SOL qty * sale price - purchase_price * qty_delivered = (0 - 32.5) * 2 = -65")
            freeze.tick(delta=datetime.timedelta(seconds=2))

            # SOL quantity=0, qty_delivered=2-1=1, returned = 1
            self._make_in_move(self.product_avco_auto, 2, 17.5)  # force different standard_price
            self.assertEqual(self.product_avco_auto.standard_price, 30, "standard_price for avco = (10 * 32.5 + 2 * 17.5) / (10 + 2) = 30: 2 delivered, 10 remaining + 2 added to stock")
            freeze.tick(delta=datetime.timedelta(seconds=2))
            stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(active_id=delivery.id, active_model='stock.picking'))
            stock_return_picking = stock_return_picking_form.save()
            stock_return_picking.product_return_moves.quantity = 1.0
            stock_return_picking_action = stock_return_picking.action_create_returns()
            return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
            return_pick.button_validate()
            self.assertEqual(sol3.product_uom_qty, 0)
            self.assertEqual(sol3.qty_delivered, 1)
            # purchase_unit_from_delivery = line.move_ids(done)._get_price_unit = (2 * 32.5 + 1 * 32.5) / (2 + 1) = 32.5
            self.assertEqual(sol3.purchase_price, 32.5, "purchase_price = 2 * 32.5 + 1 * 32.5) / (2 + 1) = 32.5")
            self.assertEqual(sol3.margin, -32.5, "margin = SOL qty * sale price - purchase_price * qty_delivered = (0 - 32.5) * 1 = -32.5")
