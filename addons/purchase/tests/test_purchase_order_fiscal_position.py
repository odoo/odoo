# -*- coding: utf-8 -*-
from odoo.addons.account.tests.invoice_test_common import InvoiceTestCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestPurchaseOrderFiscalPosition(InvoiceTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tax_10_price_include = cls.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })
        cls.tax_20_price_include = cls.env['account.tax'].create({
            'name': '20% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'price_include': True,
            'include_base_amount': True,
        })
        cls.tax_15_price_exclude = cls.env['account.tax'].create({
            'name': '15% excl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
        })

        cls.fiscal_position_exclude_to_include = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_position_exclude_to_include',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_15_price_exclude.id,
                    'tax_dest_id': cls.tax_10_price_include.id,
                }),
            ],
        })

        cls.fiscal_position_include_to_exclude = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_position_include_to_exclude',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_10_price_include.id,
                    'tax_dest_id': cls.tax_15_price_exclude.id,
                }),
            ],
        })

        cls.fiscal_position_include_to_include = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_position_include_to_include',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_10_price_include.id,
                    'tax_dest_id': cls.tax_20_price_include.id,
                }),
            ],
        })

        cls.product_tax_10_price_include = cls.env['product.product'].create({
            'name': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'standard_price': 110.0,
            'taxes_id': [(6, 0, cls.tax_10_price_include.ids)],
        })

        cls.product_tax_15_price_exclude = cls.env['product.product'].create({
            'name': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'standard_price': 200.0,
            'taxes_id': [(6, 0, cls.tax_15_price_exclude.ids)],
        })

    def test_fiscal_position_price_included_to_price_excluded_tax(self):
        ''' Test the purchase order when dealing with a fiscal position mapping a price-included tax set by default on a
        product. Indeed, mapping a price-included-tax to a price-excluded-tax must remove the tax amount from the
        price_unit set on the product.
        '''

        self.partner_a.property_account_position_id = self.fiscal_position_include_to_exclude

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        po_form.date_order = fields.Date.from_string('2019-01-01')
        po_form.currency_id = self.currency_data['currency']
        with po_form.order_line.new() as line_form:
            line_form.product_id = self.product_tax_10_price_include
            line_form.product_qty = 1.0
        purchase_order = po_form.save()

        # The original price_unit is 110.0. The price-included tax should be subtracted as 110.0 / 1.1 = 100.0.
        # Then, the currency should be applied (x2 in 2019) making the price_unit becoming 100.0 x 2 = 200.0.

        self.assertRecordValues(purchase_order.order_line, [{
            'product_id': self.product_tax_10_price_include.id,
            'product_qty': 1.0,
            'price_unit': 200.0,
            'taxes_id': self.tax_15_price_exclude.ids,
            'price_subtotal': 200.0,
        }])

    def test_fiscal_position_price_included_to_price_included_tax(self):
        ''' Test the purchase order when dealing with a fiscal position mapping a price-included tax set by default on a
        product. Indeed, mapping a price-included-tax to a price-included-tax must remove the tax amount from the
        price_unit set on the product and then add the tax amount from the new price-included tax.
        '''

        self.partner_a.property_account_position_id = self.fiscal_position_include_to_include

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        po_form.date_order = fields.Date.from_string('2019-01-01')
        po_form.currency_id = self.currency_data['currency']
        with po_form.order_line.new() as line_form:
            line_form.product_id = self.product_tax_10_price_include
            line_form.product_qty = 1.0
        purchase_order = po_form.save()

        # The original price_unit is 110.0. The price-included tax should be subtracted as 110.0 / 1.1 = 100.0.
        # Due to the fiscal position, the price_unit is set to 120.0 due to the 20% price-included tax.
        # Then, the currency should be applied (x2 in 2019) making the price_unit becoming 100.0 x 2 = 200.0.

        self.assertRecordValues(purchase_order.order_line, [{
            'product_id': self.product_tax_10_price_include.id,
            'product_qty': 1.0,
            'price_unit': 240.0,
            'taxes_id': self.tax_20_price_include.ids,
            'price_subtotal': 200.0,
        }])
