# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSaleCommon
from odoo.fields import Command
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestSaleOrder(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        Pricelist = cls.env['product.pricelist']
        PricelistItem = cls.env['product.pricelist.item']
        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)
        SaleOrderLine = cls.env['sale.order.line'].with_context(tracking_disable=True)

        # Create a product category
        cls.product_category_1 = cls.env['product.category'].create({
            'name': 'Product Category for pricelist',
        })
        # Create a pricelist with discount policy: percentage on services, fixed price for product_order
        cls.pricelist_discount_incl = Pricelist.create({
            'name': 'Pricelist A',
            'discount_policy': 'with_discount',
            'company_id': cls.company_data['company'].id,
        })
        PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_incl.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.company_data['product_service_order'].product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 10
        })
        PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_incl.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.company_data['product_service_delivery'].product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 20,
        })
        cls.pricelist_discount_incl_item3 = PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_incl.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.company_data['product_order_no'].product_tmpl_id.id,
            'compute_price': 'fixed',
            'fixed_price': 211,
        })

        # Create a pricelist without discount policy: formula for product_category_1 category, percentage for service_order
        cls.pricelist_discount_excl = Pricelist.create({
            'name': 'Pricelist B',
            'discount_policy': 'without_discount',
            'company_id': cls.company_data['company'].id,
        })
        PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_excl.id,
            'applied_on': '2_product_category',
            'categ_id': cls.product_category_1.id,
            'compute_price': 'formula',
            'base': 'standard_price',
            'price_discount': 10,
        })
        PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_excl.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.company_data['product_service_order'].product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 20,
        })

        # Create a pricelist without discount policy: percentage on all products
        cls.pricelist_discount_excl_global = cls.env['product.pricelist'].create({
            'name': 'Pricelist C',
            'discount_policy': 'without_discount',
            'company_id': cls.env.company.id,
            'item_ids': [(0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 54,
            })],
        })

        # create a generic Sale Order with all classical products and empty pricelist
        cls.sale_order = SaleOrder.create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        cls.sol_product_order = SaleOrderLine.create({
            'product_id': cls.company_data['product_order_no'].id,
            'product_uom_qty': 2,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = SaleOrderLine.create({
            'product_id': cls.company_data['product_service_delivery'].id,
            'product_uom_qty': 2,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = SaleOrderLine.create({
            'product_id': cls.company_data['product_service_order'].id,
            'product_uom_qty': 2,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_prod_deliver = SaleOrderLine.create({
            'product_id': cls.company_data['product_delivery_no'].id,
            'product_uom_qty': 2,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

    def test_sale_with_pricelist_discount_included(self):
        """ Test SO with the pricelist and check unit price appeared on its lines """
        # Change the pricelist
        self.sale_order.write({'pricelist_id': self.pricelist_discount_incl.id})
        # Trigger manually the computation for discount, unit price, subtotal, ...
        self.sale_order.update_prices()

        # Check that pricelist of the SO has been applied on the sale order lines or not
        for line in self.sale_order.order_line:
            if line.product_id == self.company_data['product_order_no']:
                self.assertEqual(line.price_unit, self.pricelist_discount_incl_item3.fixed_price, 'Price of product_order should be %s applied on the order line' % (self.pricelist_discount_incl_item3.fixed_price,))
            else:  # only services (service_order and service_deliver)
                for item in self.sale_order.pricelist_id.item_ids.filtered(lambda l: l.product_tmpl_id == line.product_id.product_tmpl_id):
                    price = item.percent_price
                    self.assertEqual(price, (line.product_id.list_price - line.price_unit) / line.product_id.list_price * 100, 'Pricelist of the SO should be applied on an order line %s' % (line.product_id.name,))

    def test_sale_with_pricelist_discount_excluded(self):
        """ Test SO with the pricelist 'discount displayed' and check discount and unit price appeared on its lines """
        # Add group 'Discount on Lines' to the user
        self.env.user.write({'groups_id': [(4, self.env.ref('product.group_discount_per_so_line').id)]})

        # Set product category on consumable products (for the pricelist item applying on this category)
        self.company_data['product_order_no'].write({'categ_id': self.product_category_1.id})
        self.company_data['product_delivery_no'].write({'categ_id': self.product_category_1.id})

        # Change the pricelist
        self.sale_order.write({'pricelist_id': self.pricelist_discount_excl.id})
        # Trigger manually the computation for discount, unit price, subtotal, ...
        self.sale_order.update_prices()

        # Check pricelist of the SO apply or not on order lines where pricelist contains formula that add 15% on the cost price
        for line in self.sale_order.order_line:
            if line.product_id.categ_id in self.sale_order.pricelist_id.item_ids.mapped('categ_id'):  # reduction per category (consummable only)
                for item in self.sale_order.pricelist_id.item_ids.filtered(lambda l: l.categ_id == line.product_id.categ_id):
                    self.assertEqual(line.discount, item.price_discount, "Discount should be displayed on order line %s since its category get some discount" % (line.name,))
                self.assertEqual(line.price_unit, line.product_id.standard_price, "Price unit should be the cost price for product %s" % (line.name,))
            else:
                if line.product_id == self.company_data['product_service_order']:  # reduction for this product
                    self.assertEqual(line.discount, 20.0, "Discount for product %s should be 20 percent with pricelist %s" % (line.name, self.pricelist_discount_excl.name))
                    self.assertEqual(line.price_unit, line.product_id.list_price, 'Unit price of order line should be a sale price as the pricelist not applied on the other category\'s product')
                else:  # no discount for the rest
                    self.assertEqual(line.discount, 0.0, 'Pricelist of SO should not be applied on an order line')
                    self.assertEqual(line.price_unit, line.product_id.list_price, 'Unit price of order line should be a sale price as the pricelist not applied on the other category\'s product')

    def test_fiscalposition_application(self):
        """Test application of a fiscal position mapping
        price included to price included tax
        """

        uom = self.env['uom.uom'].search([('name', '=', 'Units')])
        pricelist = self.env['product.pricelist'].search([('name', '=', 'Public Pricelist')])

        partner = self.env['res.partner'].create({
            'name': "George"
        })

        tax_fixed_incl = self.env['account.tax'].create({
            'name': "fixed include",
            'amount': '10.00',
            'amount_type': 'fixed',
            'price_include': True,
        })
        tax_fixed_excl = self.env['account.tax'].create({
            'name': "fixed exclude",
            'amount': '10.00',
            'amount_type': 'fixed',
            'price_include': False,
        })

        tax_include_src = self.env['account.tax'].create({
            'name': "Include 21%",
            'amount': 21.00,
            'amount_type': 'percent',
            'price_include': True,
        })
        tax_include_dst = self.env['account.tax'].create({
            'name': "Include 6%",
            'amount': 6.00,
            'amount_type': 'percent',
            'price_include': True,
        })
        tax_exclude_src = self.env['account.tax'].create({
            'name': "Exclude 15%",
            'amount': 15.00,
            'amount_type': 'percent',
            'price_include': False,
        })
        tax_exclude_dst = self.env['account.tax'].create({
            'name': "Exclude 21%",
            'amount': 21.00,
            'amount_type': 'percent',
            'price_include': False,
        })
        product_tmpl_a = self.env['product.template'].create({
            'name': "Voiture",
            'list_price': 121,
            'taxes_id': [(6, 0, [tax_include_src.id])]
        })

        product_tmpl_b = self.env['product.template'].create({
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [(6, 0, [tax_exclude_src.id])]
        })

        product_tmpl_c = self.env['product.template'].create({
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [(6, 0, [tax_fixed_incl.id, tax_exclude_src.id])]
        })

        product_tmpl_d = self.env['product.template'].create({
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [(6, 0, [tax_fixed_excl.id, tax_include_src.id])]
        })

        fpos_incl_incl = self.env['account.fiscal.position'].create({
            'name': "incl -> incl",
            'sequence': 1
        })

        self.env['account.fiscal.position.tax'].create({
            'position_id' :fpos_incl_incl.id,
            'tax_src_id': tax_include_src.id,
            'tax_dest_id': tax_include_dst.id
        })

        fpos_excl_incl = self.env['account.fiscal.position'].create({
            'name': "excl -> incl",
            'sequence': 2,
        })

        self.env['account.fiscal.position.tax'].create({
            'position_id' :fpos_excl_incl.id,
            'tax_src_id': tax_exclude_src.id,
            'tax_dest_id': tax_include_dst.id
        })

        fpos_incl_excl = self.env['account.fiscal.position'].create({
            'name': "incl -> excl",
            'sequence': 3,
        })

        self.env['account.fiscal.position.tax'].create({
            'position_id' :fpos_incl_excl.id,
            'tax_src_id': tax_include_src.id,
            'tax_dest_id': tax_exclude_dst.id
        })

        fpos_excl_excl = self.env['account.fiscal.position'].create({
            'name': "excl -> excp",
            'sequence': 4,
        })

        self.env['account.fiscal.position.tax'].create({
            'position_id' :fpos_excl_excl.id,
            'tax_src_id': tax_exclude_src.id,
            'tax_dest_id': tax_exclude_dst.id
        })

        # Create the SO with one SO line and apply a pricelist and fiscal position on it
        # Then check if price unit and price subtotal matches the expected values

        # Test Mapping included to included
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_incl_incl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_a.product_variant_id.name
            line.product_id = product_tmpl_a.product_variant_id
            line.product_uom_qty = 1.0
            line.product_uom = uom
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 106, 'price_subtotal': 100}])

        # Test Mapping excluded to included
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_excl_incl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_b.product_variant_id.name
            line.product_id = product_tmpl_b.product_variant_id
            line.product_uom_qty = 1.0
            line.product_uom = uom
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 94.34}])

        # Test Mapping included to excluded
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_incl_excl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_a.product_variant_id.name
            line.product_id = product_tmpl_a.product_variant_id
            line.product_uom_qty = 1.0
            line.product_uom = uom
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 100}])

        # Test Mapping excluded to excluded
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_excl_excl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_b.product_variant_id.name
            line.product_id = product_tmpl_b.product_variant_id
            line.product_uom_qty = 1.0
            line.product_uom = uom
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 100}])

        # Test Mapping (included,excluded) to (included, included)
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_excl_incl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_c.product_variant_id.name
            line.product_id = product_tmpl_c.product_variant_id
            line.product_uom_qty = 1.0
            line.product_uom = uom
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 84.91}])

        # Test Mapping (excluded,included) to (excluded, excluded)
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_incl_excl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_d.product_variant_id.name
            line.product_id = product_tmpl_d.product_variant_id
            line.product_uom_qty = 1.0
            line.product_uom = uom
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 100}])

    def test_pricelist_application(self):
        """ Test different prices are correctly applied based on dates """
        support_product = self.env['product.product'].create({
            'name': 'Virtual Home Staging',
            'list_price': 100,
        })
        partner = self.env['res.partner'].create(dict(name="George"))

        christmas_pricelist = self.env['product.pricelist'].create({
            'name': 'Christmas pricelist',
            'item_ids': [(0, 0, {
                'date_start': "2017-12-01",
                'date_end': "2017-12-24",
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 20,
                'applied_on': '3_global',
                'name': 'Pre-Christmas discount'
            }), (0, 0, {
                'date_start': "2017-12-25",
                'date_end': "2017-12-31",
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 50,
                'applied_on': '3_global',
                'name': 'Post-Christmas super-discount'
            })]
        })

        # Create the SO with pricelist based on date
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'date_order': '2017-12-20',
            'pricelist_id': christmas_pricelist.id,
            'order_line': [Command.create({'product_id': support_product.id})]
        })
        # Check the unit price and subtotal of SO line
        self.assertEqual(so.order_line[0].price_unit, 80, "First date pricelist rule not applied")
        self.assertEqual(so.order_line[0].price_subtotal, so.order_line[0].price_unit * so.order_line[0].product_uom_qty, 'Total of SO line should be a multiplication of unit price and ordered quantity')

        # Change order date of the SO and check the unit price and subtotal of SO line
        so.date_order = '2017-12-30'
        so.update_prices()

        self.assertEqual(so.order_line[0].price_unit, 50, "Second date pricelist rule not applied")
        self.assertEqual(so.order_line[0].price_subtotal, so.order_line[0].price_unit * so.order_line[0].product_uom_qty, 'Total of SO line should be a multiplication of unit price and ordered quantity')

    def test_pricelist_uom_discount(self):
        """ Test prices and discounts are correctly applied based on date and uom"""
        computer_case = self.env['product.product'].create({
            'name': 'Drawer Black',
            'list_price': 100,
        })
        partner = self.env['res.partner'].create(dict(name="George"))
        categ_unit_id = self.ref('uom.product_uom_categ_unit')
        goup_discount_id = self.ref('product.group_discount_per_so_line')
        self.env.user.write({'groups_id': [(4, goup_discount_id, 0)]})
        new_uom = self.env['uom.uom'].create({
            'name': '10 units',
            'factor_inv': 10,
            'uom_type': 'bigger',
            'rounding': 1.0,
            'category_id': categ_unit_id
        })
        christmas_pricelist = self.env['product.pricelist'].create({
            'name': 'Christmas pricelist',
            'discount_policy': 'without_discount',
            'item_ids': [(0, 0, {
                'date_start': "2017-12-01",
                'date_end': "2017-12-30",
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 10,
                'applied_on': '3_global',
                'name': 'Christmas discount'
            })]
        })

        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'date_order': '2017-12-20',
            'pricelist_id': christmas_pricelist.id,
        })

        order_line = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': computer_case.id,
        })

        self.assertEqual(order_line.price_subtotal, 90, "Christmas discount pricelist rule not applied")
        self.assertEqual(order_line.discount, 10, "Christmas discount not equalt to 10%")
        order_line.product_uom = new_uom
        self.assertEqual(order_line.price_subtotal, 900, "Christmas discount pricelist rule not applied")
        self.assertEqual(order_line.discount, 10, "Christmas discount not equalt to 10%")

    def test_pricelist_based_on_other(self):
        """ Test price and discount are correctly applied with a pricelist based on an other one"""
        computer_case = self.env['product.product'].create({
            'name': 'Drawer Black',
            'list_price': 100,
        })
        partner = self.env['res.partner'].create(dict(name="George"))
        goup_discount_id = self.ref('product.group_discount_per_so_line')
        self.env.user.write({'groups_id': [(4, goup_discount_id, 0)]})

        first_pricelist = self.env['product.pricelist'].create({
            'name': 'First pricelist',
            'discount_policy': 'without_discount',
            'item_ids': [(0, 0, {
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 10,
                'applied_on': '3_global',
                'name': 'First discount'
            })]
        })

        second_pricelist = self.env['product.pricelist'].create({
            'name': 'Second pricelist',
            'discount_policy': 'without_discount',
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'base': 'pricelist',
                'base_pricelist_id': first_pricelist.id,
                'price_discount': 10,
                'applied_on': '3_global',
                'name': 'Second discount'
            })]
        })

        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'date_order': '2018-07-11',
            'pricelist_id': second_pricelist.id,
        })

        order_line = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': computer_case.id,
        })

        self.assertEqual(order_line.price_subtotal, 81, "Second pricelist rule not applied")
        self.assertEqual(order_line.discount, 19, "Second discount not applied")

    def test_pricelist_with_other_currency(self):
        """ Test prices are correctly applied with a pricelist with an other currency"""
        computer_case = self.env['product.product'].create({
            'name': 'Drawer Black',
            'list_price': 100,
        })
        # computer_case.list_price = 100
        partner = self.env['res.partner'].create(dict(name="George"))
        categ_unit_id = self.ref('uom.product_uom_categ_unit')
        other_currency = self.env['res.currency'].create({
            'name': 'other currency',
            'symbol': 'other'
        })
        self.env['res.currency.rate'].create({'name': '2018-07-11',
            'rate': 2.0,
            'currency_id': other_currency.id,
            'company_id': self.env.company.id
        })
        self.env['res.currency.rate'].search(
            [('currency_id', '=', self.env.company.currency_id.id)]
        ).unlink()
        new_uom = self.env['uom.uom'].create({
            'name': '10 units',
            'factor_inv': 10,
            'uom_type': 'bigger',
            'rounding': 1.0,
            'category_id': categ_unit_id
        })

        # This pricelist doesn't show the discount
        first_pricelist = self.env['product.pricelist'].create({
            'name': 'First pricelist',
            'currency_id': other_currency.id,
            'discount_policy': 'with_discount',
            'item_ids': [(0, 0, {
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 10,
                'applied_on': '3_global',
                'name': 'First discount'
            })]
        })

        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'date_order': '2018-07-12',
            'pricelist_id': first_pricelist.id,
        })

        order_line = self.env['sale.order.line'].new({
            'order_id': so.id,
            'product_id': computer_case.id,
        })

        # force compute uom and prices
        self.assertEqual(order_line.price_unit, 180, "First pricelist rule not applied")
        order_line.product_uom = new_uom
        self.assertEqual(order_line.price_unit, 1800, "First pricelist rule not applied")

    def test_sale_change_of_pricelists_excluded_value_discount(self):
        """ Test SO with the pricelist 'discount displayed' and check displayed percentage value after multiple changes of pricelist """
        self.env.user.groups_id += self.env.ref('product.group_discount_per_so_line')

        # Create a product with a very low price
        amazing_product = self.env['product.product'].create({
            'name': 'Amazing Product',
            'lst_price': 0.03,
        })

        # create a simple Sale Order with a unique line
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [(0, 0, {
                'name': amazing_product.name,
                'product_id': amazing_product.id,
                'product_uom_qty': 1,
                'product_uom': amazing_product.uom_id.id,
                'price_unit': 0.03,
                'tax_id': False,
            })],
        })

        # Change the pricelist
        sale_order.write({'pricelist_id': self.pricelist_discount_excl_global.id})
        # Update Prices
        sale_order.update_prices()

        # Check that the discount displayed is the correct one
        self.assertEqual(
            sale_order.order_line.discount, 54,
            "Wrong discount computed for specified product & pricelist"
        )
        # Additional to check for overall consistency
        self.assertEqual(
            sale_order.order_line.price_unit, 0.03,
            "Wrong unit price computed for specified product & pricelist"
        )
        self.assertEqual(
            sale_order.order_line.price_subtotal, 0.01,
            "Wrong subtotal price computed for specified product & pricelist"
        )
        self.assertFalse(
            sale_order.order_line.tax_id,
            "Wrong tax applied for specified product & pricelist"
        )

    def test_sale_change_of_pricelists_excluded_value_discount_on_tax_included_price_mapped_to_tax_excluded_price(self):
        self.env.user.write({'groups_id': [(4, self.env.ref('product.group_discount_per_so_line').id)]})

        # setting up the taxes:
        tax_a = self.tax_sale_a.copy()
        tax_b = self.tax_sale_a.copy()
        tax_a.price_include = True
        tax_b.amount = 6

        # setting up fiscal position:
        fiscal_pos = self.fiscal_pos_a.copy()
        fiscal_pos.auto_apply = True
        country = self.env["res.country"].search([('name', '=', 'Belgium')], limit=1)
        fiscal_pos.country_id = country
        fiscal_pos.tax_ids = [
            (0, None,
             {
                 'tax_src_id': tax_a.id,
                 'tax_dest_id': tax_b.id
             })
        ]

        # setting up partner:
        self.partner_a.country_id = country

        # creating product:

        my_product = self.env['product.product'].create({
            'name': 'my Product',
            'lst_price': 115,
            'taxes_id': [tax_a.id]
        })

        # creating SO

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [(0, 0, {
                'name': my_product.name,
                'product_id': my_product.id,
                'product_uom_qty': 1,
                'product_uom': my_product.uom_id.id,
            })],
        })

        # Apply fiscal position

        sale_order.fiscal_position_id = fiscal_pos.id
        # Change the pricelist
        sale_order.write({'pricelist_id': self.pricelist_discount_excl_global.id})
        # Update Prices
        sale_order.update_prices()


        # Check that the discount displayed is the correct one
        self.assertEqual(
            sale_order.order_line.discount, 54,
            "Wrong discount computed for specified product & pricelist"
        )
        # Additional to check for overall consistency
        self.assertEqual(
            sale_order.order_line.price_unit, 100,
            "Wrong unit price computed for specified product & pricelist"
        )
        self.assertEqual(
            sale_order.order_line.price_subtotal, 46,
            "Wrong subtotal price computed for specified product & pricelist"
        )
        self.assertEqual(
            sale_order.order_line.tax_id.id, tax_b.id,
            "Wrong tax applied for specified product & pricelist"
        )
