from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account_online_synchronization.tests.common import AccountOnlineSynchronizationCommon


@tagged('post_install', '-at_install')
class TestAccountOnlineLinkPayment(AccountOnlineSynchronizationCommon):

    @patch("odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._update_connection_status")
    def test_update_status_when_payment_enabled(self, patched_update_connection_status):
        self.account_online_link.provider_type = 'provider_A'

        patched_update_connection_status.return_value = {
            'consent_expiring_date': None,
            'is_payment_enabled': True,
            'is_payment_activated': False,
        }
        self.account_online_link._update_connection_status()
        self.assertEqual(self.account_online_link.provider_type, 'provider_A_payment')

    @patch("odoo.addons.account_online_synchronization.models.account_online.AccountOnlineLink._update_connection_status")
    def test_update_status_when_payment_deactivated(self, patched_update_connection_status):
        self.account_online_link.provider_type = 'provider_A_payment_activated'

        patched_update_connection_status.return_value = {
            'consent_expiring_date': None,
            'is_payment_enabled': True,
            'is_payment_activated': False,
        }
        self.account_online_link._update_connection_status()
        self.assertEqual(self.account_online_link.provider_type, 'provider_A_payment')

    def test_check_status_journal_not_connected(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[20.0], post=True)
        payment = self._register_payment(
            invoice,
            amount=20.0,
            journal_id=self.outbound_payment_method_line.journal_id.id,
            payment_method_line_id=self.outbound_payment_method_line.id,
        )
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.outbound_payment_method_line.journal_id.id,
            'payment_ids': [Command.set(payment.ids)],
            'payment_method_id': self.outbound_payment_method_line.payment_method_id.id,
        })
        with self.assertRaisesRegex(UserError, 'This journal needs to be connected to a bank to check its status.'):
            batch.check_online_payment_status()
