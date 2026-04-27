# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from unittest.mock import MagicMock


@tagged('post_install', '-at_install')
class AccountOnlineSynchronizationCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')

        cls.euro_bank_journal = cls.env['account.journal'].create({
            'name': 'Euro Bank Journal',
            'type': 'bank',
            'code': 'EURB',
            'currency_id': cls.other_currency.id,
        })
        cls.account_online_link = cls.env['account.online.link'].create({
            'name': 'Test Bank',
            'client_id': 'client_id_1',
            'refresh_token': 'refresh_token',
            'access_token': 'access_token',
        })
        cls.account_online_account = cls.env['account.online.account'].create({
            'name': 'MyBankAccount',
            'account_online_link_id': cls.account_online_link.id,
            'journal_ids': [Command.set(cls.euro_bank_journal.id)]
        })
        cls.BankStatementLine = cls.env['account.bank.statement.line']

    def setUp(self):
        super().setUp()
        self.transaction_id = 1
        self.account_online_account.balance = 0.0

    def _create_one_online_transaction(self, transaction_identifier=None, date=None, payment_ref=None, amount=10.0, partner_name=None, foreign_currency_code=None, amount_currency=8.0):
        """ This method allows to create an online transaction granularly

            :param transaction_identifier: Online identifier of the transaction, by default transaction_id from the
                                           setUp. If used, transaction_id is not incremented.
            :param date: Date of the transaction, by default the date of today
            :param payment_ref: Label of the transaction
            :param amount: Amount of the transaction, by default equals 10.0
            :param foreign_currency_code: Code of transaction's foreign currency
            :param amount_currency: Amount of transaction in foreign currency, update transaction only if foreign_currency_code is given, by default equals 8.0
            :return: A dictionnary representing an online transaction (not formatted)
        """
        transaction_identifier = transaction_identifier if transaction_identifier is not None else self.transaction_id
        if date:
            date = date if isinstance(date, str) else fields.Date.to_string(date)
        else:
            date = fields.Date.to_string(fields.Date.today())

        payment_ref = payment_ref or f'transaction_{transaction_identifier}'
        transaction = {
            'online_transaction_identifier': transaction_identifier,
            'date': date,
            'payment_ref': payment_ref,
            'amount': amount,
            'partner_name': partner_name,
        }
        if foreign_currency_code:
            transaction.update({
                'foreign_currency_code': foreign_currency_code,
                'amount_currency': amount_currency
            })
        return transaction

    def _create_online_transactions(self, dates):
        """ This method returns a list of transactions with the
            given dates.
            All amounts equals 10.0

            :param dates: A list of dates, one transaction is created for each given date.
            :return: A formatted list of transactions
        """
        transactions = []
        for date in dates:
            transactions.append(self._create_one_online_transaction(date=date))
            self.transaction_id += 1
        return self.account_online_account._format_transactions(transactions)

    def _mock_odoofin_response(self, data=None):
        if not data:
            data = {}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': data,
        }
        return mock_response

    def _mock_odoofin_error_response(self, code=200, message='Default', data=None):
        if not data:
            data = {}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'error': {
                'code': code,
                'message': message,
                'data': data,
            },
        }
        return mock_response
