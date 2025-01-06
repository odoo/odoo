# -*- coding: utf-8 -*-

from ast import literal_eval
from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.models.account_payment_method import AccountPaymentMethod
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import Form, tagged
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

        self.company_data['default_journal_sale'].code = "DIFFERENT"
        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
        })

        with self.assertRaisesRegex(UserError, "entries linked to it"), self.cr.savepoint():
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

    def test_account_journal_duplicates(self):
        new_journals = self.env["account.journal"].with_context(import_file=True).create([
            {"name": "OD_BLABLA"},
            {"name": "OD_BLABLU"},
        ])

        self.assertEqual(sorted(new_journals.mapped("code")), ["GEN1", "OD_BL"], "The journals should be set correctly")

    def test_archive_used_journal(self):
        journal = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': 'A',
        })
        check_method = self.env['account.payment.method'].sudo().create({
                'name': 'Test',
                'code': 'check_printing_expense_test',
                'payment_type': 'outbound',
        })
        self.env['account.payment.method.line'].create({
            'name': 'Check',
            'payment_method_id': check_method.id,
            'journal_id': journal.id
            })
        with self.assertRaises(ValidationError):
            journal.action_archive()

    def test_archive_multiple_journals(self):
        journals = self.env['account.journal'].create([{
                'name': 'Test Journal 1',
                'type': 'sale',
                'code': 'A1'
            }, {
                'name': 'Test Journal 2',
                'type': 'sale',
                'code': 'A2'
            }])

        # Archive the Journals
        journals.action_archive()
        self.assertFalse(journals[0].active)
        self.assertFalse(journals[1].active)

        # Unarchive the Journals
        journals.action_unarchive()
        self.assertTrue(journals[0].active)
        self.assertTrue(journals[1].active)


@tagged('post_install', '-at_install', 'mail_alias')
class TestAccountJournalAlias(AccountTestInvoicingCommon, MailCommon):

    def test_alias_name_creation(self):
        """ Test alias creation, notably avoid raising constraints due to ascii
        characters removal. See odoo/odoo@339cdffb68f91eb1455d447d1bdd7133c68723bd """
        # check base test data
        journal1 = self.company_data['default_journal_purchase']
        company1 = journal1.company_id
        journal2 = self.company_data_2['default_journal_sale']
        company2 = journal2.company_id
        # have a non ascii company name
        company2.name = 'ぁ'

        for (aname, jname, jcode, jtype, jcompany), expected_alias_name in zip(
            [
                ('youpie', 'Journal Name', 'NEW1', 'purchase', company1),
                (False, 'Journal Other Name', 'NEW2', 'purchase', company1),
                (False, 'ぁ', 'NEW3', 'purchase', company1),
                (False, 'ぁ', 'ぁ', 'purchase', company1),
                ('youpie', 'Journal Name', 'NEW1', 'purchase', company2),
                (False, 'Journal Other Name', 'NEW2', 'purchase', company2),
                (False, 'ぁ', 'NEW3', 'purchase', company2),
                (False, 'ぁ', 'ぁ', 'purchase', company2),
            ],
            [
                f'youpie-{company1.name}',
                f'journal-other-name-{company1.name}',
                f'new3-{company1.name}',
                f'purchase-{company1.name}',
                f'youpie-{company2.id}',
                f'journal-other-name-{company2.id}',
                f'new3-{company2.id}',
                f'purchase-{company2.id}',
            ]
        ):
            with self.subTest(aname=aname, jname=jname, jcode=jcode, jtype=jtype, jcompany=jcompany):
                new_journal = self.env['account.journal'].create({
                    'code': jcode,
                    'company_id': jcompany.id,
                    'name': jname,
                    'type': jtype,
                    # force alias_name only if given, to check default value otherwise
                    **({'alias_name': aname} if aname else {}),
                })
                self.assertEqual(new_journal.alias_name, expected_alias_name)

        # other types: no mail support by default
        journals = self.env['account.journal'].create([{
            'code': f'NEW{jtype}',
            'name': f'Type {jtype}',
            'type': jtype}
            for jtype in ('general', 'cash', 'bank')
        ])
        self.assertFalse(journals.alias_id, 'Do not create useless aliases')
        self.assertFalse(list(filter(None, journals.mapped('alias_name'))))

    def test_alias_name_form(self):
        """ Test alias name update using Form tool (onchange) """
        journal = Form(self.env['account.journal'])
        journal.name = 'Test With Form'
        self.assertFalse(journal.alias_name)
        journal.type = 'sale'
        self.assertEqual(journal.alias_name, f'test-with-form-{self.env.company.name}')
        journal.type = 'cash'
        self.assertFalse(journal.alias_name)

    def test_alias_from_type(self):
        """ Test alias behavior on journal, especially alias_name management as
        well as defaults update, see odoo/odoo@400b6860271a11b9914166ff7e42939c4c6192dc """
        journal = self.company_data['default_journal_purchase']

        # assert base test data
        company_name = 'company_1_data'
        journal_code = 'BILL'
        journal_name = 'Vendor Bills'
        journal_alias = journal.alias_id
        self.assertEqual(journal.code, journal_code)
        self.assertEqual(journal.company_id.name, company_name)
        self.assertEqual(journal.name, journal_name)
        self.assertEqual(journal.type, 'purchase')

        # assert default creation data
        self.assertEqual(journal_alias.alias_contact, 'everyone')
        self.assertDictEqual(
            dict(literal_eval(journal_alias.alias_defaults)),
            {
                'move_type': 'in_invoice',
                'company_id': journal.company_id.id,
                'journal_id': journal.id,
            }
        )
        self.assertFalse(journal_alias.alias_force_thread_id, 'Journal alias should create new moves')
        self.assertEqual(journal_alias.alias_model_id, self.env['ir.model']._get('account.move'),
                         'Journal alias targets moves')
        self.assertEqual(journal_alias.alias_name, f'vendor-bills-{company_name}')
        self.assertEqual(journal_alias.alias_parent_model_id, self.env['ir.model']._get('account.journal'),
                         'Journal alias owned by journal itself')
        self.assertEqual(journal_alias.alias_parent_thread_id, journal.id,
                         'Journal alias owned by journal itself')

        # update alias_name, ensure a fallback on a real name when not explicit reset
        for alias_name, expected in [
            (False, False),
            ('', False),
            (' ', f'vendor-bills-{company_name}'),  # error recuperation
            ('.', f'vendor-bills-{company_name}'),  # error recuperation
            ('😊', f'vendor-bills-{company_name}'),  # resets, unicode not supported
            ('ぁ', f'vendor-bills-{company_name}'),  # resets, non ascii not supported
            ('Youpie Boum', 'youpie-boum'),
        ]:
            with self.subTest(alias_name=alias_name):
                journal.write({'alias_name': alias_name})
                self.assertEqual(journal.alias_name, expected)
                self.assertEqual(journal_alias.alias_name, expected)

        # changing type should void if not purchase or sale
        for jtype in ('general', 'cash', 'bank'):
            journal.write({'type': jtype})
            self.assertEqual(journal.alias_id, journal_alias,
                             'Dà not unlink aliases, just reset their value')
            self.assertFalse(journal.alias_name)
            self.assertFalse(journal_alias.alias_name)

        # changing type should reset if sale or purchase
        journal.company_id.write({'name': 'New Company Name'})
        journal.write({'name': 'Reset Journal', 'type': 'sale'})
        journal_alias_2 = journal.alias_id
        self.assertEqual(journal_alias_2.alias_contact, 'everyone')
        self.assertDictEqual(
            dict(literal_eval(journal_alias_2.alias_defaults)),
            {
                'move_type': 'out_invoice',
                'company_id': journal.company_id.id,
                'journal_id': journal.id,
            }
        )
        self.assertFalse(journal_alias_2.alias_force_thread_id, 'Journal alias should create new moves')
        self.assertEqual(journal_alias_2.alias_model_id, self.env['ir.model']._get('account.move'),
                         'Journal alias targets moves')
        self.assertEqual(journal_alias_2.alias_name, 'reset-journal-new-company-name')
        self.assertEqual(journal_alias_2.alias_parent_model_id, self.env['ir.model']._get('account.journal'),
                         'Journal alias owned by journal itself')
        self.assertEqual(journal_alias_2.alias_parent_thread_id, journal.id,
                         'Journal alias owned by journal itself')

    def test_alias_create_unique(self):
        """ Make auto-generated alias_name unique when needed """
        company_name = self.company_data['company'].name
        journal = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': 'A',
        })
        journal2 = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': 'B',
        })
        self.assertEqual(journal.alias_name, f'test-journal-{company_name}')
        self.assertEqual(journal2.alias_name, f'test-journal-{company_name}-b')
