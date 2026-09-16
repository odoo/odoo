# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import (
    AccountEdiProxyError,
)
from odoo.addons.l10n_cn_edi_baiwang.models.account_edi_proxy_user import (
    AccountEdiProxyClientUser,
)
from odoo.addons.l10n_cn_edi_baiwang.models.baiwang_client import BaiwangClient


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCnBaiwangFlow(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('cn')
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data['company']
        company.write({
            'vat': '91310115MA1K39423D',
            'l10n_cn_baiwang_org_auth_code': 'demo-org',
            'l10n_cn_baiwang_subscription_status': 'authorized',
        })
        cls.partner_a.country_id = cls.env.ref('base.cn')

        tax_cat = cls.env['l10n_cn_edi.tax.category'].sudo().create({'name': 'Test', 'code': '1010101010000000000'})
        cls.product_a.product_tmpl_id.l10n_cn_tax_category_id = tax_cat.id
        cls.product_b.product_tmpl_id.l10n_cn_tax_category_id = tax_cat.id

        private_key = cls.env['certificate.key']._generate_rsa_private_key(company, name='baiwang_test_proxy_key_global')
        cls.env['account_edi_proxy_client.user'].create({
            'id_client': 'baiwang-test-client-global',
            'company_id': company.id,
            'edi_identification': company.vat,
            'private_key_id': private_key.id,
            'proxy_type': 'l10n_cn_edi_baiwang',
            'edi_mode': company.l10n_cn_edi_mode,
            'refresh_token': 'ZGVtbw==',
        })
        company._compute_l10n_cn_baiwang_proxy_user_id()

    def setUp(self):
        super().setUp()
        # Patch the ORM class directly to avoid fragile string-path patches.
        proxy_class = self.env['account_edi_proxy_client.user'].__class__

        patch.object(proxy_class, '_make_request',
                     return_value={'id_client': 'mock_id', 'refresh_token': 'mock_token'}).start()

        patch.object(proxy_class, '_l10n_cn_baiwang_contact_proxy',
                     return_value={'success': True, 'response': {'success': True}, 'subscription_status': 'authorized', 'org_auth_code': 'mock_org'}).start()

        self.addCleanup(patch.stopall)

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
        client = BaiwangClient(company)

        result = client.query_invoice({'foo': 'bar'})
        self.assertEqual(result, {'success': True})

    def test_03b_structured_error_with_known_reference(self):
        company = self.company_data['company']
        client = BaiwangClient(company)

        def fake_proxy_call(_company, _payload):
            return {'success': False, 'error': {'reference': 'invalid_payload', 'data': {'message': 'bad payload'}}}

        with self.assertRaises(UserError) as err:
            client._call_proxy(fake_proxy_call, {'foo': 'bar'}, error_prefix='Baiwang proxy error: %(error)s')
        self.assertIn('The Baiwang request payload is invalid.', str(err.exception))

    def test_03c_provider_error_with_known_code(self):
        company = self.company_data['company']
        client = BaiwangClient(company)

        def fake_proxy_call(_company, _payload):
            return {
                'success': False,
                'error': {
                    'reference': 'provider_error',
                    'data': {'code': '101', 'message': 'token rejected'},
                },
            }

        with self.assertRaises(UserError) as err:
            client._call_proxy(fake_proxy_call, {'foo': 'bar'}, error_prefix='Baiwang proxy error: %(error)s')
        self.assertIn('Authentication failed. Please verify your Baiwang credentials.', str(err.exception))
        self.assertIn('Baiwang [101]: token rejected', str(err.exception))

    def test_03d_provider_error_with_unknown_code(self):
        company = self.company_data['company']
        client = BaiwangClient(company)

        def fake_proxy_call(_company, _payload):
            return {
                'success': False,
                'error': {
                    'reference': 'provider_error',
                    'data': {'code': '777777', 'message': 'upstream rejected request'},
                },
            }

        with self.assertRaises(UserError) as err:
            client._call_proxy(fake_proxy_call, {'foo': 'bar'}, error_prefix='Baiwang proxy error: %(error)s')
        self.assertIn('Baiwang error [777777]: upstream rejected request', str(err.exception))

    def test_03e_malformed_error_payload_fallback(self):
        company = self.company_data['company']
        client = BaiwangClient(company)

        def fake_proxy_call(_company, _payload):
            return {'success': False, 'error': []}

        with self.assertRaises(UserError) as err:
            client._call_proxy(fake_proxy_call, {'foo': 'bar'}, error_prefix='Baiwang proxy error: %(error)s')
        self.assertIn('Unexpected Baiwang proxy error.', str(err.exception))

    def test_03f_proxy_structured_error_passthrough(self):
        company = self.company_data['company']
        proxy_user = company.l10n_cn_baiwang_proxy_user_id
        proxy_class = self.env['account_edi_proxy_client.user'].__class__

        expected = {
            'success': False,
            'error': {
                'reference': 'provider_error',
                'data': {'code': 'X-CODE', 'message': 'provider message'},
            },
        }
        with patch.object(proxy_class, '_l10n_cn_baiwang_contact_proxy', return_value=expected):
            result = proxy_user._l10n_cn_baiwang_query_invoice(company, {'foo': 'bar'})

        self.assertFalse(result['success'])
        self.assertEqual(result['error']['reference'], 'provider_error')
        self.assertEqual(result['error']['data']['code'], 'X-CODE')
        self.assertEqual(result['error']['data']['message'], 'provider message')

    def test_03g_proxy_structured_api_error_mapping(self):
        company = self.company_data['company']
        client = BaiwangClient(company)

        def fake_proxy_call(_company, _payload):
            return {
                'success': False,
                'error': {
                    'reference': 'baiwang_api_error',
                    'data': {'code': '101', 'message': 'token rejected'},
                },
            }

        with self.assertRaises(UserError) as err:
            client._call_proxy(fake_proxy_call, {'foo': 'bar'}, error_prefix='Baiwang proxy error: %(error)s')
        self.assertIn('Authentication failed. Please verify your Baiwang credentials.', str(err.exception))
        self.assertIn('Baiwang [101]: token rejected', str(err.exception))

    def test_04_subscribe_action_gets_portal_url_from_proxy(self):
        company = self.company_data['company']
        settings = self.env['res.config.settings'].create({'company_id': company.id})
        proxy_class = self.env['account_edi_proxy_client.user'].__class__

        proxy_url = 'https://www-pre.baiwang.com/portal/subscribe/abc123'
        with patch.object(
            proxy_class, '_l10n_cn_baiwang_contact_proxy',
            return_value={'success': True, 'url': proxy_url},
        ):
            action = settings.action_l10n_cn_baiwang_subscribe()

        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertEqual(action['url'], proxy_url)
        self.assertEqual(action['target'], 'new')

    def test_04b_subscribe_action_raises_without_url_in_response(self):
        company = self.company_data['company']
        settings = self.env['res.config.settings'].create({'company_id': company.id})
        proxy_class = self.env['account_edi_proxy_client.user'].__class__

        with patch.object(
            proxy_class, '_l10n_cn_baiwang_contact_proxy',
            return_value={'success': True},
        ):
            with self.assertRaises(UserError) as err:
                settings.action_l10n_cn_baiwang_subscribe()
        self.assertIn('Could not retrieve the Baiwang subscription URL.', str(err.exception))

    def test_04c_authorize_action_gets_portal_url_from_proxy(self):
        company = self.company_data['company']
        settings = self.env['res.config.settings'].create({'company_id': company.id})
        proxy_class = self.env['account_edi_proxy_client.user'].__class__

        proxy_url = 'https://www-pre.baiwang.com/portal/authorize/abc123'
        with patch.object(
            proxy_class, '_l10n_cn_baiwang_contact_proxy',
            return_value={'success': True, 'url': proxy_url},
        ):
            action = settings.action_l10n_cn_baiwang_authorize()

        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertEqual(action['url'], proxy_url)
        self.assertEqual(action['target'], 'new')

    def test_04d_authorize_action_requires_subscription(self):
        company = self.company_data['company']
        company.l10n_cn_baiwang_subscription_status = 'not_subscribed'
        settings = self.env['res.config.settings'].create({'company_id': company.id})

        with self.assertRaises(UserError) as err:
            settings.action_l10n_cn_baiwang_authorize()
        self.assertIn('Please complete Baiwang subscription first.', str(err.exception))

    def test_05_red_form_required_only_for_draft_refund_of_issued_invoice(self):
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

    def test_06_send_print_registers_and_uses_baiwang_extra_edi(self):
        invoice = self._create_posted_invoice()
        send_model = self.env['account.move.send']

        all_extra_edis = send_model._get_all_extra_edis()
        self.assertIn('cn_baiwang', all_extra_edis)
        self.assertTrue(all_extra_edis['cn_baiwang']['is_applicable'](invoice))

        invoices_data = {
            invoice: {
                'extra_edis': {'cn_baiwang'},
            },
        }
        with patch.object(invoice.__class__, '_l10n_cn_baiwang_issue_invoice', return_value='Proxy error'):
            send_model._call_web_service_before_invoice_pdf_render(invoices_data)

        self.assertIn('error', invoices_data[invoice])
        self.assertIn('Proxy error', invoices_data[invoice]['error']['errors'])

    def test_07_red_form_status_cron_handles_empty_queue(self):
        # Cron runs as superuser in production; use sudo here to mirror it.
        self.env['l10n_cn_edi.document'].sudo()._cron_check_red_form_status()

    def test_08_red_form_pending_to_confirmed_lifecycle(self):
        """Mock the B2B workflow where a red form goes to Pending, then is approved by the buyer."""
        invoice = self._create_posted_invoice()
        invoice.l10n_cn_baiwang_invoice_no = '24442000000071309399'

        # 1. Create the Reversal (Credit Note)
        wizard = self.env['account.move.reversal'].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
        ).create({
            'journal_id': invoice.journal_id.id,
            'reason': 'Customer rejected goods',
            'l10n_cn_baiwang_red_form_type': '02',
        })
        wizard.reverse_moves()
        credit_note = wizard.new_move_ids

        # 2. Mock the Red Form Request to return '02' (Pending)
        pending_response = {
            'success': True,
            'response': [{
                'redConfirmUuid': 'mock-uuid-123',
                'redConfirmNo': 'mock-no-456',
                'confirmState': '02',
            }],
        }

        # Patch the ORM class directly; string-path patches can miss dynamic model classes.
        proxy_class = self.env['account_edi_proxy_client.user'].__class__

        with patch.object(
            proxy_class, '_l10n_cn_baiwang_contact_proxy',
            return_value={'success': True, 'response': pending_response},
        ):
            credit_note.action_request_baiwang_red_form()

        # Assert UI state changed to pending
        edi_doc = credit_note.l10n_cn_edi_document_ids[0]
        self.assertEqual(edi_doc.state, 'red_form_pending')
        self.assertEqual(credit_note.l10n_cn_baiwang_red_form_status, 'red_form_pending')

        # 3. Mock the Cron Job polling Baiwang and discovering it is now '01' (Approved)
        approved_response = {
            'success': True,
            'response': [{
                'confirmState': '01',
                'redConfirmNo': 'mock-no-456',
                'redInvoiceNo': 'mock-red-fapiao-789',
                # 'redInvoiceDate': '20260715123000',
            }],
        }

        # _cron_check_red_form_status validates outbound red forms for this workflow.
        proxy_class = self.env['account_edi_proxy_client.user'].__class__
        with patch.object(
            proxy_class, '_l10n_cn_baiwang_contact_proxy',
            return_value=approved_response,
        ):
            self.env['l10n_cn_edi.document'].sudo()._cron_check_red_form_status()

        # Assert UI state fully resolved and Fapiao number populated
        self.assertEqual(edi_doc.state, 'red_form_confirmed')
        self.assertEqual(credit_note.l10n_cn_baiwang_red_form_status, 'red_form_confirmed')
        self.assertEqual(credit_note.l10n_cn_baiwang_state, 'issued')
        self.assertEqual(credit_note.l10n_cn_baiwang_invoice_no, 'mock-red-fapiao-789')

    def test_08c_red_form_reuses_single_document(self):
        invoice = self._create_posted_invoice()
        invoice.l10n_cn_baiwang_invoice_no = '24442000000071309399'

        wizard = self.env['account.move.reversal'].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
        ).create({
            'journal_id': invoice.journal_id.id,
            'reason': 'Customer rejected goods',
            'l10n_cn_baiwang_red_form_type': '02',
        })
        wizard.reverse_moves()
        credit_note = wizard.new_move_ids

        pending_response = {
            'success': True,
            'response': [{
                'redConfirmUuid': 'mock-uuid-123',
                'redConfirmNo': 'mock-no-456',
                'confirmState': '02',
            }],
        }

        proxy_class = self.env['account_edi_proxy_client.user'].__class__
        with patch.object(
            proxy_class, '_l10n_cn_baiwang_contact_proxy',
            return_value={'success': True, 'response': pending_response},
        ):
            credit_note.action_request_baiwang_red_form()

        red_docs = credit_note.l10n_cn_edi_document_ids
        self.assertEqual(len(red_docs), 1)
        self.assertEqual(red_docs.state, 'red_form_pending')

        with self.assertRaises(UserError):
            credit_note.action_request_baiwang_red_form()
        red_docs = credit_note.l10n_cn_edi_document_ids
        self.assertEqual(len(red_docs), 1)

    def test_09_proportional_global_discount(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'price_unit': 600.0, 'quantity': 1.0}),
                (0, 0, {'product_id': self.product_b.id, 'price_unit': 900.0, 'quantity': 2.0}),
                (0, 0, {'name': 'Global Discount', 'price_unit': -240.0, 'quantity': 1.0}),
            ],
        })
        payload_lines = invoice._l10n_cn_baiwang_prepare_lines()
        self.assertEqual(len(payload_lines), 4)
        self.assertEqual(payload_lines[1]['invoiceLineNature'], '1')
        self.assertEqual(payload_lines[3]['invoiceLineNature'], '1')
        self.assertAlmostEqual(payload_lines[1]['goodsTotalPrice'], -60.0)
        self.assertAlmostEqual(payload_lines[3]['goodsTotalPrice'], -180.0)

    def _contact_proxy_with_error(self, code):
        """Call the real _l10n_cn_baiwang_contact_proxy with _make_request raising the given proxy error code."""
        proxy_user = self.env['account_edi_proxy_client.user'].search([
            ('proxy_type', '=', 'l10n_cn_edi_baiwang'),
        ], limit=1)
        with patch.object(
            self.env['account_edi_proxy_client.user'].__class__, '_make_request',
            side_effect=AccountEdiProxyError(code, 'boom'),
        ):
            with self.assertRaises(UserError) as ctx:
                AccountEdiProxyClientUser._l10n_cn_baiwang_contact_proxy(proxy_user, '/api/foo', {})
        return ctx.exception.args[0]

    def test_11_registration_uses_dedicated_connect_route(self):
        company = self.company_data['company']
        proxy_class = self.env['account_edi_proxy_client.user'].__class__

        calls = {}

        def fake_make_request(url, params=False, **kwargs):
            calls['url'] = url
            calls['params'] = params
            return {'id_client': 'new_id_client', 'refresh_token': 'new_refresh_token'}

        with patch.object(proxy_class, '_make_request', side_effect=fake_make_request):
            new_user = self.env['account_edi_proxy_client.user']._l10n_cn_baiwang_create_proxy_user(
                company,
                'prod',
            )

        self.assertTrue(calls['url'].endswith('/api/l10n_cn_edi_baiwang/1/connect'))
        self.assertEqual(calls['params']['tax_no'], company.vat)
        self.assertEqual(calls['params']['dbuuid'], self.env['ir.config_parameter'].get_str('database.uuid'))
        self.assertEqual(calls['params']['company_id'], company.id)
        self.assertIn('BEGIN PUBLIC KEY', base64.b64decode(calls['params']['public_key']).decode())

        self.assertEqual(new_user.id_client, 'new_id_client')
        self.assertEqual(new_user.refresh_token, 'new_refresh_token')
        self.assertEqual(new_user.edi_identification, company.vat)
        self.assertEqual(new_user.proxy_type, 'l10n_cn_edi_baiwang')
        self.assertEqual(new_user.edi_mode, 'prod')
        self.assertTrue(new_user.private_key_id)

    def test_10_proxy_rate_limit_error_is_mapped(self):
        self.assertIn('maximum number of requests', self._contact_proxy_with_error('proxy_rate_limit_exceeded'))

    def test_10b_proxy_other_error_is_generic(self):
        self.assertIn('Failed to contact the Baiwang proxy service', self._contact_proxy_with_error('connection_error'))

    def test_10c_proxy_string_error_does_not_crash(self):
        client = BaiwangClient(self.company_data['company'])
        with self.assertRaises(UserError) as ctx:
            client._call_proxy(
                lambda company, *args: {'success': False, 'error': 'string error'},
                {},
                error_prefix='Baiwang proxy error: %(error)s',
            )
        self.assertIn('string error', ctx.exception.args[0])
