# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment_sepa_direct_debit.tests.common import SepaDirectDebitCommon


@tagged('post_install', '-at_install')
class TestSepaDirectDebit(SepaDirectDebitCommon):

    def test_transactions_are_confirmed_as_soon_as_mandate_is_valid(self):
        token = self._create_token(provider_ref=self.mandate.name, sdd_mandate_id=self.mandate.id)
        tx = self._create_transaction(flow='token', token_id=token.id)

        tx._send_payment_request()
        self.assertEqual(tx.state, 'done', "SEPA transactions should be immediately confirmed.")

    def test_bank_statement_confirms_transaction_and_mandate(self):
        tx = self._create_transaction(flow='direct', state='pending', mandate_id=self.mandate.id)
        AccountBankStatementLine = self.env['account.bank.statement.line']
        AccountBankStatementLine.create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'partner_id': self.mandate.partner_id.id,
            'amount_currency': tx.amount,
            'foreign_currency_id': tx.currency_id.id,
            'payment_ref': tx.reference,
        })
        AccountBankStatementLine._cron_confirm_sepa_transactions()
        self.assertEqual(tx.state, 'done')

    def test_confirming_transaction_creates_token(self):
        tx = self._create_transaction(flow='direct', state='pending', mandate_id=self.mandate.id)
        tx._set_done()
        token = self.env['payment.token'].search([('sdd_mandate_id', '=', self.mandate.id)])
        self.assertTrue(token)
        self.assertTrue(token.active)
        self.assertEqual(tx.token_id, token)
        self.assertEqual(self.mandate.state, 'active')

    def test_creating_batch_payment_generates_export_file(self):
        """ Test the XML generation when validating a batch payment. """
        sdd_provider_method_line = self.company_data['default_journal_bank'] \
            .inbound_payment_method_line_ids.filtered(lambda l: l.code == 'sepa_direct_debit')
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_id': self.partner.id,
            'amount': 100.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': sdd_provider_method_line.id,
        })
        payment.action_post()

        batch_payment = self.env['account.batch.payment'].create(
            {
                'journal_id': payment.journal_id.id,
                'payment_method_id': payment.payment_method_id.id,
                'payment_ids': [
                    (Command.set(payment.ids))
                ],
            }
        )
        batch_payment.validate_batch_button()

        self.assertTrue(batch_payment.export_file)
