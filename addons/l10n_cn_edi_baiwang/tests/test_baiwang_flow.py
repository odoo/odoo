# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_cn_edi_baiwang.models.baiwang_client import BaiwangClient


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCnBaiwangFlow(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('cn')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'vat': '91310000TEST12345X',
            'l10n_cn_baiwang_app_key': 'app-key',
            'l10n_cn_baiwang_app_secret': 'app-secret',
            'l10n_cn_baiwang_username': 'demo-user',
            'l10n_cn_baiwang_password': 'demo-password',
            'l10n_cn_baiwang_salt': 'demo-salt',
            'l10n_cn_baiwang_org_auth_code': 'demo-org',
        })
        cls.partner_a.country_id = cls.env.ref('base.cn')

    def _create_posted_invoice(self):
        invoice = self.init_invoice(
            'out_invoice',
            partner=self.partner_a,
            products=self.product_a,
            taxes=self.tax_sale_a,
        )
        invoice.action_post()
        return invoice

    def test_01_offline_issue_does_not_mark_failed(self):
        invoice = self._create_posted_invoice()

        with patch(
            'odoo.addons.l10n_cn_edi_baiwang.models.account_move.BaiwangClient.ensure_connection',
            side_effect=UserError('Offline: DNS failure'),
        ), patch(
            'odoo.addons.l10n_cn_edi_baiwang.models.account_move.BaiwangClient.issue_invoice',
            side_effect=AssertionError('issue_invoice should not be called when connectivity precheck fails'),
        ):
            error_message = invoice._l10n_cn_baiwang_issue_invoice()

        self.assertEqual(error_message, 'Offline: DNS failure')
        self.assertNotEqual(invoice.l10n_cn_baiwang_state, 'failed')
        self.assertFalse(invoice.l10n_cn_baiwang_error_message)
        self.assertFalse(invoice.l10n_cn_baiwang_serial_no)

    def test_02_reversal_wizard_propagates_red_form_reason(self):
        invoice = self._create_posted_invoice()

        wizard = self.env['account.move.reversal'].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
        ).create({
            'journal_id': invoice.journal_id.id,
            'reason': 'placeholder',
            'l10n_cn_baiwang_red_form_type': '02',
        })
        wizard.reverse_moves()

        self.assertEqual(wizard.new_move_ids.move_type, 'out_refund')
        self.assertEqual(wizard.new_move_ids.l10n_cn_baiwang_red_form_type, '02')

    def test_03_call_api_blocks_when_connectivity_check_fails(self):
        client = BaiwangClient(self.company_data['company'])

        with patch.object(client, 'ensure_connection', side_effect=UserError('No network')), patch.object(
            client,
            '_get_token',
            side_effect=AssertionError('_get_token should not be called when offline'),
        ):
            with self.assertRaisesRegex(UserError, 'No network'):
                client.call_api('baiwang.output.invoice.query', body={}, version='6.0')
