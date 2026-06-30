# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

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

    def _create_baiwang_proxy_user(self, suffix='default'):
        company = self.company_data['company']
        private_key = self.env['certificate.key']._generate_rsa_private_key(company, name=f'baiwang_test_proxy_key_{suffix}')
        proxy_user = self.env['account_edi_proxy_client.user'].create({
            'id_client': f'baiwang-test-client-{suffix}',
            'company_id': company.id,
            'edi_identification': company.vat,
            'private_key_id': private_key.id,
            'proxy_type': 'l10n_cn_edi_baiwang',
            'edi_mode': company.l10n_cn_edi_mode,
            'refresh_token': 'ZGVtbw==',
        })
        company._compute_l10n_cn_baiwang_proxy_user_id()
        return proxy_user

    def test_01_offline_issue_does_not_mark_failed(self):
        invoice = self._create_posted_invoice()
        self._create_baiwang_proxy_user('issue-offline')

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

    def test_03_call_api_routes_through_proxy_wrapper(self):
        company = self.company_data['company']
        self._create_baiwang_proxy_user('call-api')
        client = BaiwangClient(company)

        with patch(
            'odoo.addons.l10n_cn_edi_baiwang.models.account_edi_proxy_user.AccountEdiProxyClientUser._l10n_cn_baiwang_call_api',
            return_value={'success': True, 'response': {'success': True}},
        ) as proxy_call:
            result = client.call_api('baiwang.output.invoice.query', body={'foo': 'bar'}, version='6.0')

        self.assertEqual(result, {'success': True})
        self.assertTrue(proxy_call.called)

    def test_04_subscribe_action_uses_iap_callback_url(self):
        company = self.company_data['company']
        settings = self.env['res.config.settings'].create({'company_id': company.id})

        action = settings.action_l10n_cn_baiwang_subscribe()

        self.assertEqual(action['type'], 'ir.actions.act_url')
        parsed = urlparse(action['url'])
        query = parse_qs(parsed.query)
        self.assertEqual(query.get('taxNo'), [company.vat])
        self.assertTrue(query.get('requestId'))
        self.assertTrue(query.get('callbackUrl'))
        self.assertIn('/l10n_cn_edi_baiwang/callback/order_complete', query['callbackUrl'][0])
        self.assertIn('requestId=', query['callbackUrl'][0])

    def test_05_sync_registration_status_requires_proxy_user(self):
        company = self.company_data['company']
        settings = self.env['res.config.settings'].create({'company_id': company.id})

        with self.assertRaisesRegex(UserError, 'Register Proxy User'):
            settings.action_l10n_cn_baiwang_sync_registration_status()

    def test_06_sync_registration_status_updates_company_when_proxy_available(self):
        company = self.company_data['company']
        self._create_baiwang_proxy_user('sync')
        settings = self.env['res.config.settings'].create({'company_id': company.id})

        with patch(
            'odoo.addons.l10n_cn_edi_baiwang.models.account_edi_proxy_user.AccountEdiProxyClientUser._l10n_cn_baiwang_contact_proxy',
            return_value={
                'success': True,
                'subscription_status': 'authorized',
                'org_auth_code': 'org-from-proxy',
            },
        ) as proxy_call:
            settings.action_l10n_cn_baiwang_sync_registration_status()

        self.assertTrue(proxy_call.called)
        self.assertEqual(company.l10n_cn_baiwang_subscription_status, 'authorized')
        self.assertEqual(company.l10n_cn_baiwang_org_auth_code, 'org-from-proxy')

    def test_07_red_form_required_only_for_draft_refund_of_issued_invoice(self):
        invoice = self._create_posted_invoice()
        invoice.l10n_cn_baiwang_invoice_no = '24442000000071309399'

        wizard = self.env['account.move.reversal'].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
        ).create({
            'journal_id': invoice.journal_id.id,
            'reason': 'placeholder',
            'l10n_cn_baiwang_red_form_type': '01',
        })
        wizard.reverse_moves()
        credit_note = wizard.new_move_ids

        self.assertEqual(credit_note.state, 'draft')
        self.assertTrue(credit_note.l10n_cn_baiwang_red_form_required)

    def test_08_fetch_tax_code_requires_proxy_user(self):
        product = self.product_a.product_tmpl_id

        with self.assertRaisesRegex(UserError, 'Register Proxy User'):
            product.action_fetch_baiwang_tax_code()

    def test_09_send_print_registers_and_uses_baiwang_extra_edi(self):
        invoice = self._create_posted_invoice()
        self._create_baiwang_proxy_user('send-print')
        send_model = self.env['account.move.send']

        all_extra_edis = send_model._get_all_extra_edis()
        self.assertIn('cn_baiwang', all_extra_edis)
        self.assertTrue(all_extra_edis['cn_baiwang']['is_applicable'](invoice))

        invoices_data = {
            invoice: {
                'extra_edis': {'cn_baiwang'},
            },
        }
        with patch.object(type(invoice), '_l10n_cn_baiwang_issue_invoice', return_value='Proxy error'):
            send_model._call_web_service_before_invoice_pdf_render(invoices_data)

        self.assertIn('error', invoices_data[invoice])
        self.assertIn('Proxy error', invoices_data[invoice]['error']['errors'])

    def test_10_red_form_status_cron_handles_empty_queue(self):
        self.env['l10n_cn_edi.document']._cron_check_red_form_status()
