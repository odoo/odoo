# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestAngloSaxonAccounting(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        (cls.company_data['company'] + cls.company_data_2['company']).write({'anglo_saxon_accounting': True})
        # fifo and real_time will be only set for company_A as product.category is company dependant
        product_category = cls.env['product.category'].create({
            'name': 'a random storable product category',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        cls.storable_product = cls.env['product.product'].create({
            'name': 'storable product a',
            'type': 'product',
            'categ_id': product_category.id,
        })

    def test_cogs_should_use_price_from_the_right_company(self):
        """
        Reproduce the flow of creating an invoice from a sale order with company A
        and posting the invoice with both companies selected and company B as the main.
        """
        company_a_data = self.company_data
        company_b_data = self.company_data_2
        product = self.storable_product

        # set different cost price for the same product in the 2 companies
        company_a_standard_price = 20.0
        product.with_context(force_company=company_a_data['company'].id).standard_price = company_a_standard_price
        company_b_standard_price = 10.0
        product.with_context(force_company=company_b_data['company'].id).standard_price = company_b_standard_price

        # create sale order with company A in draft (by default, self.env.user.company_id is company A)
        company_a_order = self.env['sale.order'].create({
            'name': 'testing sale order',
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': 'product storable product a',
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'product_uom': product.uom_id.id,
                    'price_unit': 40.0,
                })
            ],
        })
        company_a_order.action_confirm()

        # Create an invoice from the sale order using the sale wizard
        self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [company_a_order.id],
            'active_id': company_a_order.id,
            'default_journal_id': company_a_data['default_journal_sale'].id
        }).create({
            'advance_payment_method': 'delivered'
        }).create_invoices()
        company_a_invoice = company_a_order.invoice_ids

        # Post the invoice from company A with company B
        company_a_invoice.with_context(force_company=company_b_data['company'].id).action_post()

        # check cost used for anglo_saxon_line is from company A
        anglo_saxon_lines = company_a_invoice.line_ids.filtered('is_anglo_saxon_line')
        self.assertRecordValues(anglo_saxon_lines, [
            {'debit': 0.0, 'credit': company_a_standard_price},
            {'debit': company_a_standard_price, 'credit': 0.0},
        ])
