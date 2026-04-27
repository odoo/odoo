# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo import Command, fields, tools
from odoo.addons.account_online_synchronization.tests.common import AccountOnlineSynchronizationCommon
from odoo.tests import tagged

_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class TestAccountOnlineAccount(AccountOnlineSynchronizationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bank_account_id = cls.env['account.account'].create({
            'name': 'Bank Account',
            'account_type': 'asset_cash',
            'code': cls.env['account.account']._search_new_account_code('BNK100'),
        })
        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'A bank journal',
            'default_account_id': cls.bank_account_id.id,
            'type': 'bank',
            'code': cls.env['account.journal'].get_next_bank_cash_default_code('bank', cls.company_data['company']),
        })

    @freeze_time('2023-08-01')
    def test_get_filtered_transactions(self):
        """ This test verifies that duplicate transactions are filtered """
        self.BankStatementLine.with_context(skip_statement_line_cron_trigger=True).create({
            'date': '2023-08-01',
            'journal_id': self.euro_bank_journal.id,
            'online_transaction_identifier': 'ABCD01',
            'payment_ref': 'transaction_ABCD01',
            'amount': 10.0,
        })

        transactions_to_filtered = [
            self._create_one_online_transaction(transaction_identifier='ABCD01'),
            self._create_one_online_transaction(transaction_identifier='ABCD02'),
        ]

        filtered_transactions = self.account_online_account._get_filtered_transactions(transactions_to_filtered)

        self.assertEqual(
            filtered_transactions,
            [
                {
                    'payment_ref': 'transaction_ABCD02',
                    'date': '2023-08-01',
                    'online_transaction_identifier': 'ABCD02',
                    'amount': 10.0,
                    'partner_name': None,
                }
            ]
        )

    @freeze_time('2023-08-01')
    def test_get_filtered_transactions_with_empty_transaction_identifier(self):
        """ This test verifies that transactions without a transaction identifier
            are not filtered due to their empty transaction identifier.
        """
        self.BankStatementLine.with_context(skip_statement_line_cron_trigger=True).create({
            'date': '2023-08-01',
            'journal_id': self.euro_bank_journal.id,
            'online_transaction_identifier': '',
            'payment_ref': 'transaction_ABCD01',
            'amount': 10.0,
        })

        transactions_to_filtered = [
            self._create_one_online_transaction(transaction_identifier=''),
            self._create_one_online_transaction(transaction_identifier=''),
        ]

        filtered_transactions = self.account_online_account._get_filtered_transactions(transactions_to_filtered)

        self.assertEqual(
            filtered_transactions,
            [
                {
                    'payment_ref': 'transaction_',
                    'date': '2023-08-01',
                    'online_transaction_identifier': '',
                    'amount': 10.0,
                    'partner_name': None,
                },
                {
                    'payment_ref': 'transaction_',
                    'date': '2023-08-01',
                    'online_transaction_identifier': '',
                    'amount': 10.0,
                    'partner_name': None,
                },
            ]
        )

    @freeze_time('2023-08-01')
    def test_format_transactions(self):
        transactions_to_format = [
            self._create_one_online_transaction(transaction_identifier='ABCD01'),
            self._create_one_online_transaction(transaction_identifier='ABCD02'),
        ]
        formatted_transactions = self.account_online_account._format_transactions(transactions_to_format)
        self.assertEqual(
            formatted_transactions,
            [
                {
                    'payment_ref': 'transaction_ABCD01',
                    'date': fields.Date.from_string('2023-08-01'),
                    'online_transaction_identifier': 'ABCD01',
                    'amount': 10.0,
                    'online_account_id': self.account_online_account.id,
                    'journal_id': self.euro_bank_journal.id,
                    'company_id': self.euro_bank_journal.company_id.id,
                    'partner_name': None,
                },
                {
                    'payment_ref': 'transaction_ABCD02',
                    'date': fields.Date.from_string('2023-08-01'),
                    'online_transaction_identifier': 'ABCD02',
                    'amount': 10.0,
                    'online_account_id': self.account_online_account.id,
                    'journal_id': self.euro_bank_journal.id,
                    'company_id': self.euro_bank_journal.company_id.id,
                    'partner_name': None,
                },
            ]
        )

    @freeze_time('2023-08-01')
    def test_format_transactions_invert_sign(self):
        transactions_to_format = [
            self._create_one_online_transaction(transaction_identifier='ABCD01', amount=25.0),
        ]
        self.account_online_account.inverse_transaction_sign = True
        formatted_transactions = self.account_online_account._format_transactions(transactions_to_format)
        self.assertEqual(
            formatted_transactions,
            [
                {
                    'payment_ref': 'transaction_ABCD01',
                    'date': fields.Date.from_string('2023-08-01'),
                    'online_transaction_identifier': 'ABCD01',
                    'amount': -25.0,
                    'online_account_id': self.account_online_account.id,
                    'journal_id': self.euro_bank_journal.id,
                    'company_id': self.euro_bank_journal.company_id.id,
                    'partner_name': None,
                },
            ]
        )

    @freeze_time('2023-08-01')
    def test_format_transactions_foreign_currency_code_to_id_with_activation(self):
        """ This test ensures conversion of foreign currency code to foreign currency id and activates foreign currency if not already activate """
        gbp_currency = self.env['res.currency'].with_context(active_test=False).search([('name', '=', 'GBP')])
        egp_currency = self.env['res.currency'].with_context(active_test=False).search([('name', '=', 'EGP')])

        transactions_to_format = [
            self._create_one_online_transaction(transaction_identifier='ABCD01', foreign_currency_code='GBP'),
            self._create_one_online_transaction(transaction_identifier='ABCD02', foreign_currency_code='EGP', amount_currency=500.0),
        ]
        formatted_transactions = self.account_online_account._format_transactions(transactions_to_format)

        self.assertTrue(gbp_currency.active)
        self.assertTrue(egp_currency.active)

        self.assertEqual(
            formatted_transactions,
            [
                {
                    'payment_ref': 'transaction_ABCD01',
                    'date': fields.Date.from_string('2023-08-01'),
                    'online_transaction_identifier': 'ABCD01',
                    'amount': 10.0,
                    'online_account_id': self.account_online_account.id,
                    'journal_id': self.euro_bank_journal.id,
                    'company_id': self.euro_bank_journal.company_id.id,
                    'partner_name': None,
                    'foreign_currency_id': gbp_currency.id,
                    'amount_currency': 8.0,
                },
                {
                    'payment_ref': 'transaction_ABCD02',
                    'date': fields.Date.from_string('2023-08-01'),
                    'online_transaction_identifier': 'ABCD02',
                    'amount': 10.0,
                    'online_account_id': self.account_online_account.id,
                    'journal_id': self.euro_bank_journal.id,
                    'company_id': self.euro_bank_journal.company_id.id,
                    'partner_name': None,
                    'foreign_currency_id': egp_currency.id,
                    'amount_currency': 500.0,
                },
            ]
        )

    @freeze_time('2023-07-25')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._fetch_odoo_fin')
    def test_retrieve_pending_transactions(self, patched_fetch_odoofin):
        self.account_online_link.state = 'connected'
        patched_fetch_odoofin.side_effect = [{
            'transactions': [
                self._create_one_online_transaction(transaction_identifier='ABCD01', date='2023-07-06'),
                self._create_one_online_transaction(transaction_identifier='ABCD02', date='2023-07-22'),
            ],
            'pendings': [
                self._create_one_online_transaction(transaction_identifier='ABCD03_pending', date='2023-07-25'),
                self._create_one_online_transaction(transaction_identifier='ABCD04_pending', date='2023-07-25'),
            ]
        }]

        start_date = fields.Date.from_string('2023-07-01')
        result = self.account_online_account._retrieve_transactions(date=start_date, include_pendings=True)
        self.assertEqual(
            result,
            {
                'transactions': [
                    {
                        'payment_ref': 'transaction_ABCD01',
                        'date': fields.Date.from_string('2023-07-06'),
                        'online_transaction_identifier': 'ABCD01',
                        'amount': 10.0,
                        'partner_name': None,
                        'online_account_id': self.account_online_account.id,
                        'journal_id': self.euro_bank_journal.id,
                        'company_id': self.euro_bank_journal.company_id.id,
                    },
                    {
                        'payment_ref': 'transaction_ABCD02',
                        'date': fields.Date.from_string('2023-07-22'),
                        'online_transaction_identifier': 'ABCD02',
                        'amount': 10.0,
                        'partner_name': None,
                        'online_account_id': self.account_online_account.id,
                        'journal_id': self.euro_bank_journal.id,
                        'company_id': self.euro_bank_journal.company_id.id,
                    }
                ],
                'pendings': [
                    {
                        'payment_ref': 'transaction_ABCD03_pending',
                        'date': fields.Date.from_string('2023-07-25'),
                        'online_transaction_identifier': 'ABCD03_pending',
                        'amount': 10.0,
                        'partner_name': None,
                        'online_account_id': self.account_online_account.id,
                        'journal_id': self.euro_bank_journal.id,
                        'company_id': self.euro_bank_journal.company_id.id,
                    },
                    {
                        'payment_ref': 'transaction_ABCD04_pending',
                        'date': fields.Date.from_string('2023-07-25'),
                        'online_transaction_identifier': 'ABCD04_pending',
                        'amount': 10.0,
                        'partner_name': None,
                        'online_account_id': self.account_online_account.id,
                        'journal_id': self.euro_bank_journal.id,
                        'company_id': self.euro_bank_journal.company_id.id,
                    }
                ]
            }
        )

    @freeze_time('2023-01-01 01:10:15')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._retrieve_transactions', return_value={})
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._refresh', return_value={'success': True, 'data': {}})
    def test_basic_flow_manual_fetching_transactions(self, patched_refresh, patched_transactions):
        self.addCleanup(self.env.registry.leave_test_mode)
        # flush and clear everything for the new "transaction"
        self.env.invalidate_all()

        self.env.registry.enter_test_mode(self.cr)
        with self.env.registry.cursor() as test_cr:
            test_env = self.env(cr=test_cr)
            test_link_account = self.account_online_link.with_env(test_env)
            test_link_account.state = 'connected'
            # Call fetch_transaction in manual mode and check that a call was made to refresh and to transaction
            test_link_account._fetch_transactions()
            patched_refresh.assert_called_once()
            patched_transactions.assert_called_once()
            self.assertEqual(test_link_account.account_online_account_ids[0].fetching_status, 'done')

    @freeze_time('2023-01-01 01:10:15')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._retrieve_transactions', return_value={})
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._fetch_odoo_fin')
    def test_refresh_incomplete_fetching_transactions(self, patched_refresh, patched_transactions):
        patched_refresh.return_value = {'success': False}
        # Call fetch_transaction and if call result is false, don't call transaction
        self.account_online_link._fetch_transactions()
        patched_transactions.assert_not_called()

        patched_refresh.return_value = {'success': False, 'currently_fetching': True}
        # Call fetch_transaction and if call result is false but in the process of fetching, don't call transaction
        # and wait for the async cron to try again
        self.account_online_link._fetch_transactions()
        patched_transactions.assert_not_called()
        self.assertEqual(self.account_online_account.fetching_status, 'waiting')

    @freeze_time('2023-01-01 01:10:15')
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._retrieve_transactions', return_value={})
    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineAccount._refresh', return_value={'success': True, 'data': {}})
    def test_currently_processing_fetching_transactions(self, patched_refresh, patched_transactions):
        self.account_online_account.fetching_status = 'processing'  # simulate the fact that we are currently creating entries in odoo
        limit_time = tools.config['limit_time_real_cron'] if tools.config['limit_time_real_cron'] > 0 else tools.config['limit_time_real']
        self.account_online_link.last_refresh = datetime.now()
        with freeze_time(datetime.now() + timedelta(seconds=(limit_time - 10))):
            # Call to fetch_transaction should be skipped, and the cron should not try to fetch either
            self.account_online_link._fetch_transactions()
            self.euro_bank_journal._cron_fetch_waiting_online_transactions()
            patched_refresh.assert_not_called()
            patched_transactions.assert_not_called()

        self.addCleanup(self.env.registry.leave_test_mode)
        # flush and clear everything for the new "transaction"
        self.env.invalidate_all()

        self.env.registry.enter_test_mode(self.cr)
        with self.env.registry.cursor() as test_cr:
            test_env = self.env(cr=test_cr)
            with freeze_time(datetime.now() + timedelta(seconds=(limit_time + 100))):
                # Call to fetch_transaction should be started by the cron when the time limit is exceeded and still in processing
                self.euro_bank_journal.with_env(test_env)._cron_fetch_waiting_online_transactions()
                patched_refresh.assert_not_called()
                patched_transactions.assert_called_once()

    @patch('odoo.addons.account_online_synchronization.models.account_online.requests')
    def test_delete_with_redirect_error(self, patched_request):
        # Use case being tested: call delete on a record, first call returns token expired exception
        # Which trigger a call to get a new token, which result in a 104 user_deleted_error, since version 17,
        # such error are returned as a OdooFinRedirectException with mode link to reopen the iframe and link with a new
        # bank. In our case we don't want that and want to be able to delete the record instead.
        # Such use case happen when db_uuid has changed as the check for db_uuid is done after the check for token_validity
        account_online_link = self.env['account.online.link'].create({
            'name': 'Test Delete',
            'client_id': 'client_id_test',
            'refresh_token': 'refresh_token',
            'access_token': 'access_token',
        })
        first_call = self._mock_odoofin_error_response(code=102)
        second_call = self._mock_odoofin_error_response(code=300, data={'mode': 'link'})
        patched_request.post.side_effect = [first_call, second_call]
        nb_connections = len(self.env['account.online.link'].search([]))
        # Try to delete record
        account_online_link.unlink()
        # Record should be deleted
        self.assertEqual(len(self.env['account.online.link'].search([])), nb_connections - 1)

    @patch('odoo.addons.account_online_synchronization.models.account_online.requests')
    def test_redirect_mode_link(self, patched_request):
        # Use case being tested: Call to open the iframe which result in a OdoofinRedirectException in link mode
        # This should not trigger a traceback but delete the current online.link and reopen the iframe
        account_online_link = self.env['account.online.link'].create({
            'name': 'Test Delete',
            'client_id': 'client_id_test',
            'refresh_token': 'refresh_token',
            'access_token': 'access_token',
        })
        link_id = account_online_link.id
        first_call = self._mock_odoofin_error_response(code=300, data={'mode': 'link'})
        second_call = self._mock_odoofin_response(data={'delete': True})
        patched_request.post.side_effect = [first_call, second_call]
        # Try to open iframe with broken connection
        action = account_online_link.action_new_synchronization()
        # Iframe should open in mode link and with a different record (old one should have been deleted)
        self.assertEqual(action['params']['mode'], 'link')
        self.assertNotEqual(action['id'], link_id)
        self.assertEqual(len(self.env['account.online.link'].search([('id', '=', link_id)])), 0)

    @patch("odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._update_connection_status", return_value={})
    def test_assign_journal_with_currency_on_account_online_account(self, patched_update_connection_status):
        self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': fields.Date.from_string('2025-06-25'),
                'journal_id': self.bank_journal.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'a line',
                        'account_id': self.bank_account_id.id,
                        'debit': 100,
                        'currency_id': self.company_data['currency'].id,
                    }),
                    Command.create({
                        'name': 'another line',
                        'account_id': self.company_data['default_account_expense'].id,
                        'credit': 100,
                        'currency_id': self.company_data['currency'].id,
                    }),
                ],
            },
            {
                'move_type': 'entry',
                'date': fields.Date.from_string('2025-06-26'),
                'journal_id': self.bank_journal.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'a line',
                        'account_id': self.bank_account_id.id,
                        'debit': 220,
                        'currency_id': self.company_data['currency'].id,
                    }),
                    Command.create({
                        'name': 'another line',
                        'account_id': self.company_data['default_account_expense'].id,
                        'credit': 220,
                        'currency_id': self.company_data['currency'].id,
                    }),
                ],
            },
        ])

        self.account_online_account.currency_id = self.company_data['currency'].id
        self.account_online_account.with_context(active_id=self.bank_journal.id, active_model='account.journal')._assign_journal()
        self.assertEqual(
            self.bank_journal.currency_id.id,
            self.company_data['currency'].id,
        )
        self.assertEqual(
            self.bank_journal.default_account_id.currency_id.id,
            self.company_data['currency'].id,
        )

    @patch("odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._update_connection_status", return_value={})
    def test_set_currency_on_journal_when_existing_currencies_on_move_lines(self, patched_update_connection_status):
        bank_account_id = self.env['account.account'].create({
            'name': 'Bank Account',
            'account_type': 'asset_cash',
            'code': self.env['account.account']._search_new_account_code('BNK100'),
        })
        bank_journal = self.env['account.journal'].create({
            'name': 'A bank journal',
            'default_account_id': bank_account_id.id,
            'type': 'bank',
            'code': self.env['account.journal'].get_next_bank_cash_default_code('bank', self.company_data['company']),
        })

        self.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': fields.Date.from_string('2025-06-25'),
                'journal_id': bank_journal.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'a line',
                        'account_id': bank_account_id.id,
                        'debit': 100,
                        'currency_id': self.other_currency.id,
                    }),
                    Command.create({
                        'name': 'another line',
                        'account_id': self.company_data['default_account_expense'].id,
                        'credit': 100,
                        'currency_id': self.other_currency.id,
                    }),
                ],
            },
            {
                'move_type': 'entry',
                'date': fields.Date.from_string('2025-06-26'),
                'journal_id': bank_journal.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'a line',
                        'account_id': bank_account_id.id,
                        'debit': 220,
                        'currency_id': self.company_data['currency'].id,
                    }),
                    Command.create({
                        'name': 'another line',
                        'account_id': self.company_data['default_account_expense'].id,
                        'credit': 220,
                        'currency_id': self.company_data['currency'].id,
                    }),
                ],
            },
        ])

        self.account_online_account.currency_id = self.company_data['currency'].id
        self.account_online_account.with_context(active_id=bank_journal.id, active_model='account.journal')._assign_journal()

        # Silently ignore the error and don't set currency on the journal and on the account
        self.assertEqual(bank_journal.currency_id.id, False)
        self.assertEqual(bank_journal.default_account_id.currency_id.id, False)
