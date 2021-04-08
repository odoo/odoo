# -*- coding: utf-8 -*-
from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestSaleFiscalPosition(AccountTestInvoicingCommon):

    def test_fiscal_pos_taxes_mapping_price_included_to_price_excluded(self):
        ''' Test mapping a price-included tax (10%) with a price-excluded tax (20%) on a price_unit of 110.0.
        The price_unit should be 100.0 after applying the fiscal position.
        '''
        tax_price_include = self.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })
        tax_price_exclude = self.env['account.tax'].create({
            'name': '15% excl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
        })

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': tax_price_include.id,
                    'tax_dest_id': tax_price_exclude.id,
                }),
            ],
        })

        product = self.env['product.product'].create({
            'name': 'product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 110.0,
            'taxes_id': [(6, 0, tax_price_include.ids)],
        })

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        so_form.date_order = fields.Date.from_string('2019-01-01')
        so_form.fiscal_position_id = fiscal_position
        so_form.pricelist_id = self.env.ref('product.list0')
        with so_form.order_line.new() as line:
            line.product_id = product
        so = so_form.save()

        self.assertRecordValues(so.order_line, [{
            'price_unit': 100.0,
            'tax_id': tax_price_exclude.ids,
        }])

        uom_dozen = self.env.ref('uom.product_uom_dozen')
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line_form:
                line_form.product_uom = uom_dozen

        self.assertRecordValues(so.order_line, [{
            'price_unit': 1200.0,
            'tax_id': tax_price_exclude.ids,
        }])

    def test_fiscal_pos_taxes_mapping_price_included_to_price_included(self):
        ''' Test mapping a price-included tax (10%) with another price-included tax (20%) on a price_unit of 110.0.
        The price_unit should be 120.0 after applying the fiscal position.
        '''
        tax_price_include_1 = self.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })
        tax_price_include_2 = self.env['account.tax'].create({
            'name': '20% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'price_include': True,
            'include_base_amount': True,
        })

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': tax_price_include_1.id,
                    'tax_dest_id': tax_price_include_2.id,
                }),
            ],
        })

        product = self.env['product.product'].create({
            'name': 'product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 110.0,
            'taxes_id': [(6, 0, tax_price_include_1.ids)],
        })

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        so_form.date_order = fields.Date.from_string('2019-01-01')
        so_form.fiscal_position_id = fiscal_position
        so_form.pricelist_id = self.env.ref('product.list0')
        with so_form.order_line.new() as line:
            line.product_id = product
        so = so_form.save()

        self.assertRecordValues(so.order_line, [{
            'price_unit': 120.0,
            'tax_id': tax_price_include_2.ids,
        }])

        uom_dozen = self.env.ref('uom.product_uom_dozen')
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line_form:
                line_form.product_uom = uom_dozen

        self.assertRecordValues(so.order_line, [{
            'price_unit': 1440.0,
            'tax_id': tax_price_include_2.ids,
        }])
