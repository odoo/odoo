# -*- coding: utf-8 -*-
from odoo.addons.sale_stock.tests.test_anglo_saxon_valuation_reconciliation import TestValuationReconciliationCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAngloSaxonAccounting(TestValuationReconciliationCommon):

    def test_cogs_should_use_price_from_the_right_company(self):
        """
        Reproduce the flow of creating an invoice from a sale order with company A
        and posting the invoice with both companies selected and company B as the main.
        """
        company_a_data = self.company
        company_b_data = self._create_company()
        companies_with_b_first = company_b_data + company_a_data
        self.env.user.company_ids = companies_with_b_first
        product = self.product_standard_auto

        # set different cost price for the same product in the 2 companies
        company_a_standard_price = 20.0
        product.with_company(company_a_data).standard_price = company_a_standard_price
        company_b_standard_price = 10.0
        product.with_company(company_b_data).standard_price = company_b_standard_price

        # create sale order with company A in draft (by default, self.env.user.company_id is company A)
        self._so_deliver(product, quantity=1, price=66.0, picking=False, partner=self.vendor, date_order='2021-01-01')
        company_a_invoice = self._create_invoice(product, quantity=1, price_unit=66.0, invoice_date='2021-01-10', post=False)

        # Post the invoice from company A with company B
        company_a_invoice.with_context(allowed_company_ids=companies_with_b_first.ids).action_post()

        # check cost used for anglo_saxon_line is from company A
        anglo_saxon_lines = company_a_invoice.line_ids.filtered(lambda l: l.display_type == 'cogs')
        self.assertRecordValues(anglo_saxon_lines, [
            {'debit': 0.0, 'credit': company_a_standard_price},
            {'debit': company_a_standard_price, 'credit': 0.0},
        ])
