# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestProduct(AccountTestInvoicingCommon):

    def test_multi_company_product_tax(self):
        """ Ensure default taxes are set for all companies on products with no company set. """
        product_without_company = self.env['product.template'].with_context(allowed_company_ids=self.env.company.ids).create({
            'name': 'Product Without a Company',
        })
        product_with_company = self.env['product.template'].with_context(allowed_company_ids=self.env.company.ids).create({
            'name': 'Product With a Company',
            'company_id': self.company_data['company'].id,
        })
        companies = self.env['res.company'].sudo().search([])
        # Product should have all the default taxes of the other companies.
        self.assertRecordValues(product_without_company.sudo(), [{
            'taxes_id': companies.account_sale_tax_id.ids,
            'supplier_taxes_id': companies.account_purchase_tax_id.ids,
        }])  # Take care that inactive default taxes won't be shown on the product
        # Product should have only the default tax of the company it belongs to.
        self.assertRecordValues(product_with_company.sudo(), [{
            'taxes_id': self.company_data['company'].account_sale_tax_id.ids,
            'supplier_taxes_id': self.company_data['company'].account_purchase_tax_id.ids,
        }])
