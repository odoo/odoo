# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Date
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data


@tagged('post_install', '-at_install')
class TestAngloSaxonValuationPurchaseMRP(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAngloSaxonValuationPurchaseMRP, cls).setUpClass()
        cls.vendor01 = cls.env['res.partner'].create({'name': "Super Vendor"})

        cls.stock_input_account, cls.stock_output_account, cls.stock_valuation_account, cls.expense_account, cls.stock_journal = _create_accounting_data(cls.env)
        cls.avco_category = cls.env['product.category'].create({
            'name': 'AVCO',
            'property_cost_method': 'average',
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_journal': cls.stock_journal.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
        })

        cls.env.company.anglo_saxon_accounting = True

    def test_kit_anglo_saxo_price_diff(self):
        """
        Suppose an automated-AVCO configuration and a Price Difference Account defined on
        the product category. When buying a kit of that category at a higher price than its
        cost, the difference should be published on the Price Difference Account
        """
        price_diff_account = self.env['account.account'].create({
            'name': 'Super Price Difference Account',
            'code': 'SPDA',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        self.avco_category.property_account_creditor_price_difference_categ = price_diff_account

        kit, compo01, compo02 = self.env['product.product'].create([{
            'name': name,
            'standard_price': price,
            'type': 'product',
            'categ_id': self.avco_category.id,
        } for name, price in [('Kit', 0), ('Compo 01', 10), ('Compo 02', 20)]])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': p.id,
                'product_qty': 1,
            }) for p in [compo01, compo02]]
        })
        kit.button_bom_cost()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor01
        with po_form.order_line.new() as pol_form:
            pol_form.product_id = kit
            pol_form.price_unit = 100
        po = po_form.save()
        po.button_confirm()

        action = po.picking_ids.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()

        action = po.action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        invoice.invoice_date = Date.today()
        invoice.action_post()
        price_diff_aml = invoice.line_ids.filtered(lambda l: l.account_id == price_diff_account)
        self.assertEqual(price_diff_aml.balance, 70, "Should be the purchase price minus the kit cost (i.e. 100 - 30)")
