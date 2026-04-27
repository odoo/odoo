# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestReconciliationWidget(ValuationReconciliationTestCommon):

    def test_no_stock_account_in_reconciliation_proposition(self):
        """
        We check if no stock interim account is present in the reconcialiation proposition,
        with both standard and custom stock accounts
        """
        avco_1 = self.stock_account_product_categ.copy({'property_cost_method': 'average'})

        # We need a product category with custom stock accounts
        avco_2 = self.stock_account_product_categ.copy({
            'property_cost_method': 'average',
            'property_stock_account_input_categ_id': self.company_data['default_account_stock_in'].copy().id,
            'property_stock_account_output_categ_id': self.company_data['default_account_stock_out'].copy().id,
            'property_stock_journal': avco_1.property_stock_journal.copy().id,
            'property_stock_valuation_account_id': self.company_data['default_account_stock_valuation'].copy().id
        })

        move_1, move_2 = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'name': 'Entry 1',
                'journal_id': avco_1.property_stock_journal.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': avco_1.property_stock_account_input_categ_id.id,
                        'debit': 0.0,
                        'credit': 100.0
                    }),
                    (0, 0, {
                        'account_id': avco_1.property_stock_valuation_account_id.id,
                        'debit': 100.0,
                        'credit': 0.0
                    })
                ]
            },
            {
                'move_type': 'entry',
                'name': 'Entry 2',
                'journal_id': avco_2.property_stock_journal.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': avco_2.property_stock_account_input_categ_id.id,
                        'debit': 0.0,
                        'credit': 100.0
                    }),
                    (0, 0, {
                        'account_id': avco_2.property_stock_valuation_account_id.id,
                        'debit': 100.0,
                        'credit': 0.0
                    })
                ]
            },
        ])

        (move_1 + move_2).action_post()

        statement = self.env['account.bank.statement'].create({
            'balance_start': 0.0,
            'balance_end_real': -100.0,
            'line_ids': [(0, 0, {
                'payment_ref': 'test',
                'amount': -100.0,
                'journal_id': self.company_data['default_journal_bank'].id,
            })]
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=statement.line_ids.id).new({})
        amls = self.env['account.move.line'].search(wizard._prepare_embedded_views_data()['amls']['domain'])
        stock_accounts = (
            avco_1.property_stock_account_input_categ_id + avco_2.property_stock_account_input_categ_id
            + avco_1.property_stock_account_output_categ_id + avco_2.property_stock_account_output_categ_id
        )
        stock_res = [line for line in amls if line.account_id in stock_accounts]
        self.assertEqual(len(stock_res), 0)
