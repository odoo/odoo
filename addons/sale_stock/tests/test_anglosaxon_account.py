# -*- coding: utf-8 -*-
from odoo.addons.sale_stock.tests.test_anglo_saxon_valuation_reconciliation import TestValuationReconciliation
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestAngloSaxonAccounting(TestValuationReconciliation):

    def test_cogs_should_use_price_from_the_right_company(self):
        """
        Reproduce the flow of creating an invoice from a sale order with company A
        and posting the invoice with both companies selected and company B as the main.
        """
        company_a_data = self.company_data
        company_b_data = self.company_data_2
        companies_with_b_first = company_b_data['company'] + company_a_data['company']
        product = self.test_product_delivery

        # set different cost price for the same product in the 2 companies
        company_a_standard_price = 20.0
        product.with_company(company_a_data['company']).standard_price = company_a_standard_price
        company_b_standard_price = 10.0
        product.with_company(company_b_data['company']).standard_price = company_b_standard_price

        # create sale order with company A in draft (by default, self.env.user.company_id is company A)
        company_a_order = self._create_sale(product, '2021-01-01')
        company_a_invoice = self._create_invoice_for_so(company_a_order, product, '2021-01-10')

        # Post the invoice from company A with company B
        company_a_invoice.with_context(allowed_company_ids=companies_with_b_first.ids).action_post()

        # check cost used for anglo_saxon_line is from company A
        anglo_saxon_lines = company_a_invoice.line_ids.filtered('is_anglo_saxon_line')
        self.assertRecordValues(anglo_saxon_lines, [
            {'debit': 0.0, 'credit': company_a_standard_price},
            {'debit': company_a_standard_price, 'credit': 0.0},
        ])
