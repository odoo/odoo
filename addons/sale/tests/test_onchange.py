# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestOnchangeProductId(TransactionCase):
    """Test that when an included tax is mapped by a fiscal position, the included tax must be
    subtracted to the price of the product.
    """

    def setUp(self):
        super(TestOnchangeProductId, self).setUp()
        self.fiscal_position_model = self.env['account.fiscal.position']
        self.fiscal_position_tax_model = self.env['account.fiscal.position.tax']
        self.tax_model = self.env['account.tax']
        self.so_model = self.env['sale.order']
        self.po_line_model = self.env['sale.order.line']
        self.res_partner_model = self.env['res.partner']
        self.product_tmpl_model = self.env['product.template']
        self.product_model = self.env['product.product']
        self.product_uom_model = self.env['uom.uom']
        self.supplierinfo_model = self.env["product.supplierinfo"]
        self.pricelist_model = self.env['product.pricelist']

    def test_onchange_product_id(self):

        uom_id = self.product_uom_model.search([('name', '=', 'Units')])[0]
        pricelist = self.pricelist_model.search([('name', '=', 'Public Pricelist')])[0]

        partner_id = self.res_partner_model.create(dict(name="George"))
        tax_include_id = self.tax_model.create(dict(name="Include tax",
                                                    amount='21.00',
                                                    price_include=True,
                                                    type_tax_use='sale'))
        tax_exclude_id = self.tax_model.create(dict(name="Exclude tax",
                                                    amount='0.00',
                                                    type_tax_use='sale'))

        product_tmpl_id = self.product_tmpl_model.create(dict(name="Voiture",
                                                              list_price=121,
                                                              taxes_id=[(6, 0, [tax_include_id.id])]))

        product_id = product_tmpl_id.product_variant_id

        fp_id = self.fiscal_position_model.create(dict(name="fiscal position", sequence=1))

        fp_tax_id = self.fiscal_position_tax_model.create(dict(position_id=fp_id.id,
                                                               tax_src_id=tax_include_id.id,
                                                               tax_dest_id=tax_exclude_id.id))

        # Create the SO with one SO line and apply a pricelist and fiscal position on it
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = partner_id
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fp_id
        with order_form.order_line.new() as line:
            line.name = product_id.name
            line.product_id = product_id
            line.product_uom_qty = 1.0
            line.product_uom = uom_id
        sale_order = order_form.save()

        # Check the unit price of SO line
        self.assertEqual(100, sale_order.order_line[0].price_unit, "The included tax must be subtracted to the price")

    def test_fiscalposition_application(self):
        """Test application of a fiscal position mapping
        price included to price included tax
        """

        uom = self.product_uom_model.search([('name', '=', 'Units')])
        pricelist = self.pricelist_model.search([('name', '=', 'Public Pricelist')])

        partner = self.res_partner_model.create({
            'name': "George"
        })
        tax_fixed_incl = self.tax_model.create({
            'name': "fixed include",
            'amount': '10.00',
            'amount_type': 'fixed',
            'price_include': True,
        })
        tax_fixed_excl = self.tax_model.create({
            'name': "fixed exclude",
            'amount': '10.00',
            'amount_type': 'fixed',
            'price_include': False,
        })
        tax_include_src = self.tax_model.create({
            'name': "Include 21%",
            'amount': 21.00,
            'amount_type': 'percent',
            'price_include': True,
        })
        tax_include_dst = self.tax_model.create({
            'name': "Include 6%",
            'amount': 6.00,
            'amount_type': 'percent',
            'price_include': True,
        })
        tax_exclude_src = self.tax_model.create({
            'name': "Exclude 15%",
            'amount': 15.00,
            'amount_type': 'percent',
            'price_include': False,
        })
        tax_exclude_dst = self.tax_model.create({
            'name': "Exclude 21%",
            'amount': 21.00,
            'amount_type': 'percent',
            'price_include': False,
        })
        product_tmpl_a = self.product_tmpl_model.create({
            'name': "Voiture",
            'list_price': 121,
            'taxes_id': [(6, 0, [tax_include_src.id])]
        })

        product_tmpl_b = self.product_tmpl_model.create({
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [(6, 0, [tax_exclude_src.id])]
        })

        product_tmpl_c = self.product_tmpl_model.create({
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [(6, 0, [tax_fixed_incl.id, tax_exclude_src.id])]
        })

        product_tmpl_d = self.product_tmpl_model.create({
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [(6, 0, [tax_fixed_excl.id, tax_include_src.id])]
        })

        fpos_incl_incl = self.fiscal_position_model.create({
            'name': "incl -> incl",
            'sequence': 1
        })

        self.fiscal_position_tax_model.create({
            'position_id' :fpos_incl_incl.id,
            'tax_src_id': tax_include_src.id,
            'tax_dest_id': tax_include_dst.id
        })

        fpos_excl_incl = self.fiscal_position_model.create({
            'name': "excl -> incl",
            'sequence': 2,
        })

        self.fiscal_position_tax_model.create({
            'position_id' :fpos_excl_incl.id,
            'tax_src_id': tax_exclude_src.id,
            'tax_dest_id': tax_include_dst.id
        })

        fpos_incl_excl = self.fiscal_position_model.create({
            'name': "incl -> excl",
            'sequence': 3,
        })

        self.fiscal_position_tax_model.create({
            'position_id' :fpos_incl_excl.id,
            'tax_src_id': tax_include_src.id,
            'tax_dest_id': tax_exclude_dst.id
        })

        fpos_excl_excl = self.fiscal_position_model.create({
            'name': "excl -> excp",
            'sequence': 4,
        })

        self.fiscal_position_tax_model.create({
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
        partner = self.res_partner_model.create(dict(name="George"))

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
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = partner
        order_form.date_order = '2017-12-20'
        order_form.pricelist_id = christmas_pricelist
        with order_form.order_line.new() as line:
            line.product_id = support_product
        so = order_form.save()
        # Check the unit price and subtotal of SO line
        self.assertEqual(so.order_line[0].price_unit, 80, "First date pricelist rule not applied")
        self.assertEqual(so.order_line[0].price_subtotal, so.order_line[0].price_unit * so.order_line[0].product_uom_qty, 'Total of SO line should be a multiplication of unit price and ordered quantity')

        # Change order date of the SO and check the unit price and subtotal of SO line
        with Form(so) as order:
            order.date_order = '2017-12-30'
            with order.order_line.edit(0) as line:
                line.product_id = support_product

        self.assertEqual(so.order_line[0].price_unit, 50, "Second date pricelist rule not applied")
        self.assertEqual(so.order_line[0].price_subtotal, so.order_line[0].price_unit * so.order_line[0].product_uom_qty, 'Total of SO line should be a multiplication of unit price and ordered quantity')

    def test_pricelist_uom_discount(self):
        """ Test prices and discounts are correctly applied based on date and uom"""
        computer_case = self.env['product.product'].create({
            'name': 'Drawer Black',
            'list_price': 100,
        })
        partner = self.res_partner_model.create(dict(name="George"))
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

        order_line = self.env['sale.order.line'].new({
            'order_id': so.id,
            'product_id': computer_case.id,
        })

        # force compute uom and prices
        order_line.product_id_change()
        order_line.product_uom_change()
        order_line._onchange_discount()
        self.assertEqual(order_line.price_subtotal, 90, "Christmas discount pricelist rule not applied")
        self.assertEqual(order_line.discount, 10, "Christmas discount not equalt to 10%")
        order_line.product_uom = new_uom
        order_line.product_uom_change()
        order_line._onchange_discount()
        self.assertEqual(order_line.price_subtotal, 900, "Christmas discount pricelist rule not applied")
        self.assertEqual(order_line.discount, 10, "Christmas discount not equalt to 10%")

    def test_pricelist_based_on_other(self):
        """ Test price and discount are correctly applied with a pricelist based on an other one"""
        computer_case = self.env['product.product'].create({
            'name': 'Drawer Black',
            'list_price': 100,
        })
        partner = self.res_partner_model.create(dict(name="George"))
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

        order_line = self.env['sale.order.line'].new({
            'order_id': so.id,
            'product_id': computer_case.id,
        })

        # force compute uom and prices
        order_line.product_id_change()
        order_line._onchange_discount()
        self.assertEqual(order_line.price_subtotal, 81, "Second pricelist rule not applied")
        self.assertEqual(order_line.discount, 19, "Second discount not applied")

    def test_pricelist_with_other_currency(self):
        """ Test prices are correctly applied with a pricelist with an other currency"""
        computer_case = self.env['product.product'].create({
            'name': 'Drawer Black',
            'list_price': 100,
        })
        computer_case.list_price = 100
        partner = self.res_partner_model.create(dict(name="George"))
        categ_unit_id = self.ref('uom.product_uom_categ_unit')
        other_currency = self.env['res.currency'].create({'name': 'other currency',
            'symbol': 'other'})
        self.env['res.currency.rate'].create({'name': '2018-07-11',
            'rate': 2.0,
            'currency_id': other_currency.id,
            'company_id': self.env.company.id})
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
        order_line.product_id_change()
        self.assertEqual(order_line.price_unit, 180, "First pricelist rule not applied")
        order_line.product_uom = new_uom
        order_line.product_uom_change()
        self.assertEqual(order_line.price_unit, 1800, "First pricelist rule not applied")

    def test_sale_warnings(self):
        """Test warnings & SO/SOL updates when partner/products with sale warnings are used."""
        partner_with_warning = self.env['res.partner'].create({
            'name': 'Test', 'sale_warn': 'warning', 'sale_warn_msg': 'Highly infectious disease'})
        partner_with_block_warning = self.env['res.partner'].create({
            'name': 'Test2', 'sale_warn': 'block', 'sale_warn_msg': 'Cannot afford our services'})

        sale_order = self.env['sale.order'].create({'partner_id': partner_with_warning.id})
        warning = sale_order._onchange_partner_id_warning()
        self.assertDictEqual(warning, {
            'warning': {
                'title': "Warning for Test",
                'message': partner_with_warning.sale_warn_msg,
            },
        })

        sale_order.partner_id = partner_with_block_warning
        warning = sale_order._onchange_partner_id_warning()
        self.assertDictEqual(warning, {
            'warning': {
                'title': "Warning for Test2",
                'message': partner_with_block_warning.sale_warn_msg,
            },
        })

        # Verify partner-related fields have been correctly reset
        self.assertFalse(sale_order.partner_id.id)
        self.assertFalse(sale_order.partner_invoice_id.id)
        self.assertFalse(sale_order.partner_shipping_id.id)
        self.assertFalse(sale_order.pricelist_id.id)

        # Reuse non blocking partner for product warning tests
        sale_order.partner_id = partner_with_warning
        product_with_warning = self.env['product.product'].create({
            'name': 'Test Product', 'sale_line_warn': 'warning', 'sale_line_warn_msg': 'Highly corrosive'})
        product_with_block_warning = self.env['product.product'].create({
            'name': 'Test Product (2)', 'sale_line_warn': 'block', 'sale_line_warn_msg': 'Not produced anymore'})

        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': product_with_warning.id,
        })
        warning = sale_order_line.product_id_change()
        self.assertDictEqual(warning, {
            'warning': {
                'title': "Warning for Test Product",
                'message': product_with_warning.sale_line_warn_msg,
            },
        })

        sale_order_line.product_id = product_with_block_warning
        warning = sale_order_line.product_id_change()

        self.assertDictEqual(warning, {
            'warning': {
                'title': "Warning for Test Product (2)",
                'message': product_with_block_warning.sale_line_warn_msg,
            },
        })

        self.assertFalse(sale_order_line.product_id.id)
