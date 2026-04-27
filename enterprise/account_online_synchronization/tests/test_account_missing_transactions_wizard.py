from odoo import fields
from odoo.addons.account_online_synchronization.tests.common import AccountOnlineSynchronizationCommon
from odoo.tests import tagged
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMissingTransactionsWizard(AccountOnlineSynchronizationCommon):
    """ Tests the account journal missing transactions wizard. """

    @patch('odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._fetch_odoo_fin')
    def test_fetch_missing_transaction(self, patched_fetch_odoofin):
        self.account_online_link.state = 'connected'
        patched_fetch_odoofin.side_effect = [{
            'transactions': [
                self._create_one_online_transaction(transaction_identifier='ABCD01', date='2023-07-06', foreign_currency_code='EGP', amount_currency=8.0),
            ],
            'pendings': [
                self._create_one_online_transaction(transaction_identifier='ABCD02_pending', date='2023-07-25', foreign_currency_code='GBP', amount_currency=8.0),
            ]
        }]
        start_date = fields.Date.from_string('2023-07-01')
        wizard = self.env['account.missing.transaction.wizard'].new({
            'date': start_date,
            'journal_id': self.euro_bank_journal.id,
        })

        action = wizard.action_fetch_missing_transaction()
        transient_transactions = self.env['account.bank.statement.line.transient'].search(domain=action['domain'])
        egp_currency = self.env['res.currency'].search([('name', '=', 'EGP')])
        gbp_currency = self.env['res.currency'].search([('name', '=', 'GBP')])

        self.assertEqual(2, len(transient_transactions))
        # Posted Transaction
        self.assertEqual(transient_transactions[0]['online_transaction_identifier'], 'ABCD01')
        self.assertEqual(transient_transactions[0]['date'], fields.Date.from_string('2023-07-06'))
        self.assertEqual(transient_transactions[0]['state'], 'posted')
        self.assertEqual(transient_transactions[0]['foreign_currency_id'], egp_currency)
        self.assertEqual(transient_transactions[0]['amount_currency'], 8.0)
        # Pending Transaction
        self.assertEqual(transient_transactions[1]['online_transaction_identifier'], 'ABCD02_pending')
        self.assertEqual(transient_transactions[1]['date'], fields.Date.from_string('2023-07-25'))
        self.assertEqual(transient_transactions[1]['state'], 'pending')
        self.assertEqual(transient_transactions[1]['foreign_currency_id'], gbp_currency)
        self.assertEqual(transient_transactions[1]['amount_currency'], 8.0)
