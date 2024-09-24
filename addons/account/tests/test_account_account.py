from odoo import Command
from odoo.addons.account.tests.common import TestAccountMergeCommon
from odoo.tests import Form, tagged
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger
import psycopg2
from freezegun import freeze_time

@tagged('post_install', '-at_install')
class TestAccountAccount(TestAccountMergeCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data_2 = cls.setup_other_company()
        cls.other_currency = cls.setup_other_currency('EUR')

    def test_account_company(self):
        ''' Test that creating an account with a given company in company_ids sets the code for that company.
        Test that copying an account creates a new account with the code set for the new account's company_ids company,
        and that copying an account that belongs to multiple companies works, even if the copied account had
        check_company fields that had values belonging to several companies.
        Test that you can't have an account without a company set.
        Test that you can't remove a company from an account if there are some journal items in the company. '''

        company_1 = self.company_data['company']
        company_2 = self.company_data_2['company']
        company_3 = self.setup_other_company(name='company_3')['company']

        # Test specifying company_ids in account creation.
        account = self.env['account.account'].create({
            'code': '180001',
            'name': 'My Account in Company 2',
            'account_type': 'asset_current',
            'company_ids': [Command.link(company_2.id)]
        })
        self.assertRecordValues(
            account.with_company(company_2),
            [{'code': '180001', 'company_ids': company_2.ids}]
        )

        # Test that adding a company to an account fails if the code is not defined for that account and that company.
        with self.assertRaises(ValidationError):
            account.write({'company_ids': [Command.link(company_1.id)]})

        # Test that you can add a company to an account if you add the code at the same time
        account.write({
            'code': '180011',
            'company_ids': [Command.link(company_1.id)],
            'tax_ids': [Command.link(self.company_data['default_tax_sale'].id), Command.link(self.company_data_2['default_tax_sale'].id)],
        })
        self.assertRecordValues(account, [{'code': '180011', 'company_ids': [company_1.id, company_2.id]}])

        # Test that you can create an account with multiple codes and companies if you specify the codes in `code_mapping_ids`
        account_2 = self.env['account.account'].create({
            'code_mapping_ids': [
                Command.create({'company_id': company_1.id, 'code': '180021'}),
                Command.create({'company_id': company_2.id, 'code': '180022'}),
                Command.create({'company_id': company_3.id, 'code': '180023'}),
            ],
            'name': 'My second account',
            'account_type': 'asset_current',
            'company_ids': [Command.set([company_1.id, company_2.id, company_3.id])],
        })
        self.assertRecordValues(account_2, [{'code': '180021', 'company_ids': [company_1.id, company_2.id, company_3.id]}])
        self.assertRecordValues(account_2.with_company(company_2), [{'code': '180022'}])
        self.assertRecordValues(account_2.with_company(company_3), [{'code': '180023'}])

        # Test copying an account belonging to multiple companies, specifying the company the new account should belong to.
        account_copy_1 = account.copy({'company_ids': [Command.set(company_1.ids)], 'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)]})
        self.assertRecordValues(
            account_copy_1,
            [{'code': '180012', 'company_ids': company_1.ids, 'tax_ids': self.company_data['default_tax_sale'].ids}],
        )

        # Test copying an account belonging to multiple companies, without specifying the company. Both companies should be copied.
        account_copy_2 = account.copy()
        self.assertRecordValues(
            account_copy_2,
            [{
                'code': '180013',
                'company_ids': [company_1.id, company_2.id],
                'tax_ids': [self.company_data['default_tax_sale'].id, self.company_data_2['default_tax_sale'].id],
            }],
        )
        self.assertRecordValues(account_copy_2.with_company(company_2), [{'code': '180002'}])

        # Test copying an account belonging to 3 companies
        account_copy_3 = account_2.copy()
        self.assertRecordValues(account_copy_3, [{'code': '180022', 'company_ids': [company_1.id, company_2.id, company_3.id]}])
        self.assertRecordValues(account_copy_3.with_company(company_2), [{'code': '180023'}])
        self.assertRecordValues(account_copy_3.with_company(company_3), [{'code': '180024'}])

        # Test that at least one company is required on accounts.
        with self.assertRaises(UserError):
            self.company_data['default_account_revenue'].company_ids = False

        # Test that unassigning a company from an account fails if there already are journal items
        # for that company and that account.
        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'name': 'line_debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
                (0, 0, {
                    'name': 'line_credit',
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })

        with self.assertRaises(UserError):
            self.company_data['default_account_revenue'].company_ids = company_2

    def test_toggle_reconcile(self):
        ''' Test the feature when the user sets an account as reconcile/not reconcile with existing journal entries. '''
        account = self.company_data['default_account_revenue']

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.other_currency.id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.other_currency.id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                }),
            ],
        })
        move.action_post()
        self.env['account.move.line'].flush_model()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

        # Set the account as reconcile and fully reconcile something.
        account.reconcile = True
        self.env.invalidate_all()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 100.0, 'amount_residual_currency': 200.0},
            {'reconciled': False, 'amount_residual': -100.0, 'amount_residual_currency': -200.0},
        ])

        move.line_ids.reconcile()
        self.assertRecordValues(move.line_ids, [
            {'reconciled': True, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': True, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

        # Set back to a not reconcile account and check the journal items.
        move.line_ids.remove_move_reconcile()
        account.reconcile = False
        self.env.invalidate_all()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

    def test_toggle_reconcile_with_partials(self):
        ''' Test the feature when the user sets an account as reconcile/not reconcile with partial reconciliation. '''
        account = self.company_data['default_account_revenue']

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.other_currency.id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.other_currency.id,
                    'debit': 0.0,
                    'credit': 50.0,
                    'amount_currency': -100.0,
                }),
                (0, 0, {
                    'account_id': self.company_data['default_account_expense'].id,
                    'currency_id': self.other_currency.id,
                    'debit': 0.0,
                    'credit': 50.0,
                    'amount_currency': -100.0,
                }),
            ],
        })
        move.action_post()

        # Set the account as reconcile and partially reconcile something.
        account.reconcile = True
        self.env.invalidate_all()

        move.line_ids.filtered(lambda line: line.account_id == account).reconcile()

        # Try to set the account as a not-reconcile one.
        with self.assertRaises(UserError), self.cr.savepoint():
            account.reconcile = False

    def test_remove_account_from_account_group(self):
        """Test if an account is well removed from account group"""
        group = self.env['account.group'].create({
            'name': 'test_group',
            'code_prefix_start': 401000,
            'code_prefix_end': 402000,
            'company_id': self.env.company.id
        })

        account_1 = self.company_data['default_account_revenue'].copy({'code': 401000})
        account_2 = self.company_data['default_account_revenue'].copy({'code': 402000})

        self.assertRecordValues(account_1 + account_2, [{'group_id': group.id}] * 2)

        group.code_prefix_end = 401000

        # Because group_id must depend on the group start and end, but there is no way of making this dependency explicit.
        (account_1 | account_2).invalidate_recordset(fnames=['group_id'])

        self.assertRecordValues(account_1 + account_2, [{'group_id': group.id}, {'group_id': False}])

    def test_name_create(self):
        """name_create should only be possible when importing
           Code and Name should be split
        """
        with self.assertRaises(UserError):
            self.env['account.account'].name_create('550003 Existing Account')
        # account code is mandatory and providing a name without a code should raise an error
        with self.assertRaises(psycopg2.DatabaseError), mute_logger('odoo.sql_db'):
            self.env['account.account'].with_context(import_file=True).name_create('Existing Account')
        account_id = self.env['account.account'].with_context(import_file=True).name_create('550003 Existing Account')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550003")
        self.assertEqual(account.name, "Existing Account")

    def test_compute_account_type(self):
        existing_account = self.company_data['default_account_revenue']
        # account_type should be computed
        new_account_code = self.env['account.account']._search_new_account_code(existing_account.code)
        new_account = self.env['account.account'].create({
            'code': new_account_code,
            'name': 'A new account'
        })
        self.assertEqual(new_account.account_type, existing_account.account_type)
        # account_type should not be altered
        alternate_account = self.env['account.account'].search([
            ('account_type', '!=', existing_account.account_type),
            ('company_ids', '=', self.company_data['company'].id),
        ], limit=1)
        alternate_code = self.env['account.account']._search_new_account_code(alternate_account.code)
        new_account.code = alternate_code
        self.assertEqual(new_account.account_type, existing_account.account_type)

    def test_get_closest_parent_account(self):
        self.env['account.account'].create({
            'code': 99998,
            'name': 'This name will be transferred to the child one',
            'account_type': 'expense',
            'tag_ids': [
                Command.create({'name': 'Test tag'}),
            ],
        })
        account_to_process = self.env['account.account'].create({
            'code': 99999,
            'name': 'This name will be erase',
        })

        self.env['account.account']._get_closest_parent_account(account_to_process, "name", default_value='The name was not given by the parent')
        self.assertEqual(account_to_process.name, 'This name will be transferred to the child one')

        #  The account type and tags will be transferred automatically with the computes
        self.assertEqual(account_to_process.account_type, 'expense')
        self.assertEqual(account_to_process.tag_ids.name, 'Test tag')

    def test_search_new_account_code(self):
        """ Test whether the account codes tested for availability are the ones we expect. """
        # pylint: disable=bad-whitespace
        tests = [
            # start_code  Expected tested codes
            ('102100',    ['102101', '102102', '102103', '102104']),
            ('1598',      ['1599', '1600', '1601', '1602']),
            ('10.01.08',  ['10.01.09', '10.01.10', '10.01.11', '10.01.12']),
            ('10.01.97',  ['10.01.98', '10.01.99', '10.01.97.copy', '10.01.97.copy2']),
            ('1021A',     ['1022A', '1023A', '1024A', '1025A']),
            ('hello',     ['hello.copy', 'hello.copy2', 'hello.copy3', 'hello.copy4']),
            ('9998',      ['9999', '9998.copy', '9998.copy2', '9998.copy3']),
        ]
        for start_code, expected_tested_codes in tests:
            start_account = self.env['account.account'].create({
                'code': start_code,
                'name': 'Test',
                'account_type': 'asset_receivable',
            })
            tested_codes = [start_account.copy().code for _ in expected_tested_codes]

            self.assertListEqual(tested_codes, expected_tested_codes)

    def test_compute_current_balance(self):
        """ Test if an account's current_balance is computed correctly """

        account_payable = self.company_data['default_account_payable']
        account_receivable = self.company_data['default_account_receivable']

        payable_debit_move = {
            'line_ids': [
                (0, 0, {'name': 'debit', 'account_id': account_payable.id, 'debit': 100.0, 'credit': 0.0}),
                (0, 0, {'name': 'credit', 'account_id': account_receivable.id, 'debit': 0.0, 'credit': 100.0}),
            ],
        }
        payable_credit_move = {
            'line_ids': [
                (0, 0, {'name': 'credit', 'account_id': account_payable.id, 'debit': 0.0, 'credit': 100.0}),
                (0, 0, {'name': 'debit', 'account_id': account_receivable.id, 'debit': 100.0, 'credit': 0.0}),
            ],
        }

        self.assertEqual(account_payable.current_balance, 0)

        self.env['account.move'].create(payable_debit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, 100)

        self.env['account.move'].create(payable_credit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, 0)

        self.env['account.move'].create(payable_credit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100)

        self.env['account.move'].create(payable_credit_move).button_cancel()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100, 'Canceled invoices/bills should not be used when computing the balance')

        # draft invoice
        self.env['account.move'].create(payable_credit_move)
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100, 'Draft invoices/bills should not be used when computing the balance')

    def test_name_create_account_code_only(self):
        """
        Test account creation with only a code, with and without space
        """
        account_id = self.env['account.account'].with_context(import_file=True).name_create('550003')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550003")
        self.assertEqual(account.name, "")

        account_id = self.env['account.account'].with_context(import_file=True).name_create('550004 ')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550004")
        self.assertEqual(account.name, "")

    def test_name_create_account_name_with_number(self):
        """
        Test the case when a code is provided and the account name contains a number in the first word
        """
        account_id = self.env['account.account'].with_context(import_file=True).name_create('550005 CO2')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550005")
        self.assertEqual(account.name, "CO2")

        account_id = self.env['account.account'].with_context(import_file=True, default_account_type='expense').name_create('CO2')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "CO2")
        self.assertEqual(account.name, "")

    def test_create_account(self):
        """
        Test creating an account with code and name without name_create
        """
        account = self.env['account.account'].create({
            'code': '314159',
            'name': 'A new account',
            'account_type': 'expense',
        })
        self.assertEqual(account.code, "314159")
        self.assertEqual(account.name, "A new account")

        # name split is only possible through name_create, so an error should be raised
        with self.assertRaises(ValidationError):
            account = self.env['account.account'].create({
                'name': '314159 A new account',
                'account_type': 'expense',
            })

        # it doesn't matter whether the account name contains numbers or not
        account = self.env['account.account'].create({
            'code': '31415',
            'name': 'CO2-contributions',
            'account_type': 'expense'
        })
        self.assertEqual(account.code, "31415")
        self.assertEqual(account.name, "CO2-contributions")

    def test_account_name_onchange(self):
        """
        Test various scenarios when creating an account via a form
        """
        account_form = Form(self.env['account.account'])
        account_form.name = "A New Account 1"

        # code should not be set
        self.assertEqual(account_form.code, False)
        self.assertEqual(account_form.name, "A New Account 1")

        account_form.name = "314159 A New Account"
        # the name should be split into code and name
        self.assertEqual(account_form.code, "314159")
        self.assertEqual(account_form.name, "A New Account")

        account_form.code = False
        account_form.name = "314159 "
        # the name should be moved to code
        self.assertEqual(account_form.code, "314159")
        self.assertEqual(account_form.name, "")

        account_form.code = "314159"
        account_form.name = "CO2-contributions"
        # the name should not overwrite the code
        self.assertEqual(account_form.code, "314159")
        self.assertEqual(account_form.name, "CO2-contributions")

        account_form.code = False
        account_form.name = "CO2-contributions"
        # the name should overwrite the code
        self.assertEqual(account_form.code, "CO2-contributions")
        self.assertEqual(account_form.name, "")

        # should save the account correctly
        account_form.code = False
        account_form.name = "314159"
        account = account_form.save()
        self.assertEqual(account.code, "314159")
        self.assertEqual(account.name, "")

        # can change the name of an existing account without overwriting the code
        account_form.name = "123213 Test"
        self.assertEqual(account_form.code, "314159")
        self.assertEqual(account_form.name, "123213 Test")

        account_form.code = False
        account_form.name = "Only letters"
        # saving a form without a code should not be possible
        with self.assertRaises(ValidationError):
            account_form.save()

    @freeze_time('2023-09-30')
    def test_generate_account_suggestions(self):
        """
            Test the generation of account suggestions for a partner.

            - Creates: partner and a account move of that partner.
            - Checks if the most frequent account for the partner matches created account (with recent move).
            - Sets the account as deprecated and checks that it no longer appears in the suggestions.

            * since tested function takes into account last 2 years, we use freeze_time
        """
        partner = self.env['res.partner'].create({'name': 'partner_test_generate_account_suggestions'})
        account = self.company_data['default_account_revenue']
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '2023-09-30',
            'line_ids': [Command.create({'price_unit': 100, 'account_id': account.id})]
        })

        results_1 = self.env['account.account']._get_most_frequent_accounts_for_partner(
            company_id=self.env.company.id,
            partner_id=partner.id,
            move_type="out_invoice"
        )
        self.assertEqual(account.id, results_1[0], "Account with most account_moves should be listed first")

        account.deprecated = True
        account.flush_recordset(['deprecated'])
        results_2 = self.env['account.account']._get_most_frequent_accounts_for_partner(
            company_id=self.env.company.id,
            partner_id=partner.id,
            move_type="out_invoice"
        )
        self.assertFalse(account.id in results_2, "Deprecated account should NOT appear in account suggestions")

    @freeze_time('2017-01-01')
    def test_account_opening_balance(self):
        company = self.env.company
        account = self.company_data['default_account_revenue']
        balancing_account = company.get_unaffected_earnings_account()

        self.assertFalse(company.account_opening_move_id)

        account.opening_debit = 300
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 300.0},
            {'account_id': balancing_account.id,    'balance': -300.0},
        ])

        account.opening_credit = 500
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 300.0},
            {'account_id': account.id,              'balance': -500.0},
            {'account_id': balancing_account.id,    'balance': 200.0},
        ])

        account.opening_balance = 0
        self.cr.precommit.run()
        self.assertFalse(company.account_opening_move_id.line_ids)

        account.currency_id = self.other_currency
        account.opening_debit = 100
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': balancing_account.id,    'balance': -100.0,  'amount_currency': -100.0},
        ])

        company.account_opening_move_id.write({'line_ids': [
            Command.create({
                'account_id': account.id,
                'balance': 100.0,
                'amount_currency': 200.0,
                'currency_id': account.currency_id.id,
            }),
            Command.create({
                'account_id': balancing_account.id,
                'balance': -100.0,
            }),
        ]})
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': balancing_account.id,    'balance': -100.0,  'amount_currency': -100.0},
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': balancing_account.id,    'balance': -100.0,  'amount_currency': -100.0},
        ])

        account.opening_credit = 1000
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': account.id,              'balance': -1000.0, 'amount_currency': -2000.0},
            {'account_id': balancing_account.id,    'balance': 800.0,   'amount_currency': 800.0},
        ])

        account.opening_debit = 1000
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 1000.0,  'amount_currency': 2000.0},
            {'account_id': account.id,              'balance': -1000.0, 'amount_currency': -2000.0},
        ])

    def test_unmerge(self):
        company_1 = self.company_data['company']
        company_2 = self.company_data_2['company']

        # 1. Create a merged account.
        # First, set-up various fields pointing to the accounts before merging
        accounts = self.env['account.account']._load_records([
            {
                'xml_id': f'account.{company_1.id}_test_account_1',
                'values': {
                    'name': 'My First Account',
                    'code': '100234',
                    'account_type': 'asset_receivable',
                    'company_ids': [Command.link(company_1.id)],
                    'tax_ids': [Command.link(self.company_data['default_tax_sale'].id)],
                    'tag_ids': [Command.link(self.env.ref('account.account_tag_operating').id)],
                },
            },
            {
                'xml_id': f'account.{company_2.id}_test_account_2',
                'values': {
                    'name': 'My Second Account',
                    'code': '100235',
                    'account_type': 'asset_receivable',
                    'company_ids': [Command.link(company_2.id)],
                    'tax_ids': [Command.link(self.company_data_2['default_tax_sale'].id)],
                    'tag_ids': [Command.link(self.env.ref('account.account_tag_investing').id)],
                },
            },
        ])
        referencing_records = {
            account: self._create_references_to_account(account)
            for account in accounts
        }

        # Create the merged account by merging `accounts`
        wizard = self._create_account_merge_wizard(accounts)
        wizard.action_merge()
        self.assertFalse(accounts[1].exists())

        # Check that the merged account has correct values
        account_to_unmerge = accounts[0]
        self.assertRecordValues(account_to_unmerge, [{
            'company_ids': [company_1.id, company_2.id],
            'name': 'My First Account',
            'code': '100234',
            'tax_ids': [self.company_data['default_tax_sale'].id, self.company_data_2['default_tax_sale'].id],
            'tag_ids': [self.env.ref('account.account_tag_operating').id, self.env.ref('account.account_tag_investing').id],
        }])
        self.assertRecordValues(account_to_unmerge.with_company(company_2), [{'code': '100235'}])
        self.assertEqual(self.env['account.chart.template'].ref('test_account_1'), account_to_unmerge)
        self.assertEqual(self.env['account.chart.template'].with_company(company_2).ref('test_account_2'), account_to_unmerge)

        for referencing_records_for_account in referencing_records.values():
            for referencing_record, fname in referencing_records_for_account.items():
                expected_field_value = account_to_unmerge.ids if referencing_record._fields[fname].type == 'many2many' else account_to_unmerge.id
                self.assertRecordValues(referencing_record, [{fname: expected_field_value}])

        # Step 2: Unmerge the account
        new_account = account_to_unmerge.with_context({
            'account_unmerge_confirm': True,
            'allowed_company_ids': [company_1.id, company_2.id],
        })._action_unmerge()

        # Check that the account fields are correct
        self.assertRecordValues(account_to_unmerge, [{
            'company_ids': [company_1.id],
            'name': 'My First Account',
            'code': '100234',
            'tax_ids': self.company_data['default_tax_sale'].ids,
            'tag_ids': [self.env.ref('account.account_tag_operating').id, self.env.ref('account.account_tag_investing').id],
        }])
        self.assertRecordValues(account_to_unmerge.with_company(company_2), [{'code': False}])
        self.assertRecordValues(new_account.with_company(company_2), [{
            'company_ids': [company_2.id],
            'name': 'My First Account',
            'code': '100235',
            'tax_ids': self.company_data_2['default_tax_sale'].ids,
            'tag_ids': [self.env.ref('account.account_tag_operating').id, self.env.ref('account.account_tag_investing').id],
        }])
        self.assertRecordValues(new_account, [{'code': False}])

        # Check that the referencing records were correctly unmerged
        new_account_by_old_account = {
            account_to_unmerge: account_to_unmerge,
            accounts[1]: new_account,
        }
        for account, referencing_records_for_account in referencing_records.items():
            for referencing_record, fname in referencing_records_for_account.items():
                expected_account = new_account_by_old_account[account]
                expected_field_value = expected_account.ids if referencing_record._fields[fname].type == 'many2many' else expected_account.id
                self.assertRecordValues(referencing_record, [{fname: expected_field_value}])

        # Check that the XMLids were correctly unmerged
        self.assertEqual(self.env['account.chart.template'].ref('test_account_1'), account_to_unmerge)
        self.assertEqual(self.env['account.chart.template'].with_company(company_2).ref('test_account_2'), new_account)

    def test_account_code_mapping(self):
        company_3 = self.env['res.company'].create({'name': 'company_3'})
        account = self.env['account.account'].create({
            'code': 'test1',
            'name': 'Test Account',
            'account_type': 'asset_current',
        })

        # Write to DB so that the account gets an ID, and invalidate cache for code_mapping_ids so that they will be looked up
        account.invalidate_recordset(['code_mapping_ids'])

        account = account.with_context({'allowed_company_ids': [self.company_data['company'].id, self.company_data_2['company'].id, company_3.id]})

        with Form(account) as account_form:
            # Test that the code mapping gives correct values once the form has been opened (which should call search)
            self.assertRecordValues(account.code_mapping_ids, [
                {'company_id': self.company_data['company'].id, 'code': 'test1'},
                {'company_id': self.company_data_2['company'].id, 'code': False},
                {'company_id': company_3.id, 'code': False},
            ])

            # Test that we are able to set a new code for companies 2 and 3 via the company mapping
            with account_form.code_mapping_ids.edit(1) as code_mapping_form:
                code_mapping_form.code = 'test2'
            with account_form.code_mapping_ids.edit(2) as code_mapping_form:
                code_mapping_form.code = 'test3'

            # Test that writing codes and companies at the same time doesn't trigger the constraint
            # that the code must be set for each company in company_ids
            account_form.company_ids.add(self.company_data_2['company'])
            account_form.company_ids.add(company_3)

        self.assertRecordValues(account.with_company(self.company_data_2['company'].id), [{'code': 'test2'}])
        self.assertRecordValues(account.with_company(company_3.id), [{'code': 'test3'}])

    def test_account_code_mapping_create(self):
        """ Similar as above, except test that you can create an account while specifying multiple codes in the code mapping tab. """

        company_3 = self.env['res.company'].create({'name': 'company_3'})

        AccountAccount = self.env['account.account'].with_context(
            {'allowed_company_ids': [self.company_data['company'].id, self.company_data_2['company'].id, company_3.id]}
        )

        with Form(AccountAccount) as account_form:
            expected_code_mapping_vals_list = [
                {'company_id': self.company_data['company'].id, 'code': False},
                {'company_id': self.company_data_2['company'].id, 'code': False},
                {'company_id': company_3.id, 'code': False},
            ]
            actual_code_mapping_vals_list = account_form.code_mapping_ids._records

            for expected_code_mapping_vals, actual_code_mapping_vals in zip(expected_code_mapping_vals_list, actual_code_mapping_vals_list):
                for key, expected_val in expected_code_mapping_vals.items():
                    self.assertEqual(actual_code_mapping_vals[key], expected_val)

            account_form.name = "My Test Account"
            account_form.code = 'test1'
            with account_form.code_mapping_ids.edit(1) as code_mapping_form:
                code_mapping_form.code = 'test2'
            with account_form.code_mapping_ids.edit(2) as code_mapping_form:
                code_mapping_form.code = 'test3'

            # Test that writing codes and companies at the same time doesn't trigger the constraint
            # that the code must be set for each company in company_ids
            account_form.company_ids.add(self.company_data_2['company'])
            account_form.company_ids.add(company_3)

        account = account_form.record

        self.assertRecordValues(account, [{
            'company_ids': [self.company_data['company'].id, self.company_data_2['company'].id, company_3.id],
            'code': 'test1'
        }])
        self.assertRecordValues(account.with_company(self.company_data_2['company'].id), [{'code': 'test2'}])
        self.assertRecordValues(account.with_company(company_3.id), [{'code': 'test3'}])

    def test_account_group_hierarchy_consistency(self):
        """ Test if the hierarchy of account groups is consistent when creating, deleting and recreating an account group """
        def create_account_group(name, code_prefix, company):
            return self.env['account.group'].create({
                'name': name,
                'code_prefix_start': code_prefix,
                'code_prefix_end': code_prefix,
                'company_id': company.id
            })

        group_1 = create_account_group('group_1', 1, self.env.company)
        group_10 = create_account_group('group_10', 10, self.env.company)
        group_100 = create_account_group('group_100', 100, self.env.company)
        group_101 = create_account_group('group_101', 101, self.env.company)

        self.assertEqual(len(group_1.parent_id), 0)
        self.assertEqual(group_10.parent_id, group_1)
        self.assertEqual(group_100.parent_id, group_10)
        self.assertEqual(group_101.parent_id, group_10)

        # Delete group_101 and recreate it
        group_101.unlink()
        group_101 = create_account_group('group_101', 101, self.env.company)

        self.assertEqual(len(group_1.parent_id), 0)
        self.assertEqual(group_10.parent_id, group_1)
        self.assertEqual(group_100.parent_id, group_10)
        self.assertEqual(group_101.parent_id, group_10)
