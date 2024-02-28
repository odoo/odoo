# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.models.account_payment_method import AccountPaymentMethod
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestAccountJournal(AccountTestInvoicingCommon):

    def test_constraint_currency_consistency_with_accounts(self):
        ''' The accounts linked to a bank/cash journal must share the same foreign currency
        if specified.
        '''
        journal_bank = self.company_data['default_journal_bank']
        journal_bank.currency_id = self.currency_data['currency']

        # Try to set a different currency on the 'debit' account.
        with self.assertRaises(ValidationError), self.cr.savepoint():
            journal_bank.default_account_id.currency_id = self.company_data['currency']

    def test_changing_journal_company(self):
        ''' Ensure you can't change the company of an account.journal if there are some journal entries '''

        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
        })

        with self.assertRaises(UserError), self.cr.savepoint():
            self.company_data['default_journal_sale'].company_id = self.company_data_2['company']

    def test_account_control_create_journal_entry(self):
        move_vals = {
            'line_ids': [
                (0, 0, {
                    'name': 'debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': 'credit',
                    'account_id': self.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
        }

        # Should fail because 'default_account_expense' is not allowed.
        self.company_data['default_journal_misc'].account_control_ids |= self.company_data['default_account_revenue']
        with self.assertRaises(UserError), self.cr.savepoint():
            self.env['account.move'].create(move_vals)

        # Should be allowed because both accounts are accepted.
        self.company_data['default_journal_misc'].account_control_ids |= self.company_data['default_account_expense']
        self.env['account.move'].create(move_vals)

    def test_account_control_existing_journal_entry(self):
        self.env['account.move'].create({
            'line_ids': [
                (0, 0, {
                    'name': 'debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': 'credit',
                    'account_id': self.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
        })

        # There is already an other line using the 'default_account_expense' account.
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.company_data['default_journal_misc'].account_control_ids |= self.company_data['default_account_revenue']

        # Assigning both should be allowed
        self.company_data['default_journal_misc'].account_control_ids = \
            self.company_data['default_account_revenue'] + self.company_data['default_account_expense']

    def test_account_journal_add_new_payment_method_multi(self):
        """
        Test the automatic creation of payment method lines with the mode set to multi
        """
        Method_get_payment_method_information = AccountPaymentMethod._get_payment_method_information

        def _get_payment_method_information(self):
            res = Method_get_payment_method_information(self)
            res['multi'] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
            return res

        with patch.object(AccountPaymentMethod, '_get_payment_method_information', _get_payment_method_information):
            self.env['account.payment.method'].sudo().create({
                'name': 'Multi method',
                'code': 'multi',
                'payment_type': 'inbound'
            })

            journals = self.env['account.journal'].search([('inbound_payment_method_line_ids.code', '=', 'multi')])

            # The two bank journals have been set
            self.assertEqual(len(journals), 2)

    def test_remove_payment_method_lines(self):
        """
        Payment method lines are a bit special in the way their removal is handled.
        If they are linked to a payment at the moment of the deletion, they won't be deleted but the journal_id will be
        set to False.
        If they are not linked to any payment, they will be deleted as expected.
        """

        # Linked to a payment. It will not be deleted, but its journal_id will be set to False.
        first_method = self.inbound_payment_method_line
        self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_method_line_id': first_method.id,
        })

        first_method.unlink()

        self.assertFalse(first_method.journal_id)

        # Not linked to anything. It will be deleted.
        second_method = self.outbound_payment_method_line
        second_method.unlink()

        self.assertFalse(second_method.exists())

    def test_account_journal_alias_name(self):
        journal = self.company_data['default_journal_purchase']
        self.assertEqual(journal.alias_name, 'vendor-bills-company_1_data')
        journal.name = 'ぁ'
        journal.alias_name = False
        self.assertEqual(journal.alias_name, 'bill-company_1_data')
        journal.code = 'ぁ'
        journal.alias_name = False
        self.assertEqual(journal.alias_name, 'purchase-company_1_data')

        company_2_id = str(self.company_data_2['company'].id)
        journal_2 = self.company_data_2['default_journal_sale']
        self.company_data_2['company'].name = 'ぁ'
        journal_2.alias_name = False
        self.assertEqual(journal_2.alias_name, 'customer-invoices-' + company_2_id)
        journal_2.name = 'ぁ'
        journal_2.alias_name = False
        self.assertEqual(journal_2.alias_name, 'inv-' + company_2_id)
        journal_2.code = 'ぁ'
        journal_2.alias_name = False
        self.assertEqual(journal_2.alias_name, 'sale-' + company_2_id)

    def test_account_journal_duplicates(self):
        new_journals = self.env["account.journal"].with_context(import_file=True).create([
            {"name": "OD_BLABLA"},
            {"name": "OD_BLABLU"},
        ])

        self.assertEqual(sorted(new_journals.mapped("code")), ["GEN1", "OD_BL"], "The journals should be set correctly")
