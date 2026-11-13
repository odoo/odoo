# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import zipfile
from base64 import b64encode
from datetime import datetime
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import HOST, L10nCnEdiYunshuiTestCommon, MockResponse, MockYunshuiGateway
from odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client import (
    DOWNLOAD_INVOICE,
    GET_CREDIT_LINE,
    LOGIN,
    QUERY_RESULT,
    SIMPLE_ISSUE,
)

CLIENT = 'odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestYunshuiClient(L10nCnEdiYunshuiTestCommon):

    def setUp(self):
        super().setUp()
        self.gateway = MockYunshuiGateway(
            self.company.l10n_cn_edi_yunshui_identity_code,
            self.company.l10n_cn_edi_yunshui_platform_code,
        )
        patch('odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client.requests.post', self.gateway).start()
        patch('odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client.HOSTS', {'test': HOST, 'prod': HOST}).start()
        self.addCleanup(patch.stopall)

    def test_simple_issue_payload(self):
        invoice = self._post_invoice()
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '1000', 'message': '提交成功'}
        self.gateway.handlers[QUERY_RESULT] = {
            'code': '1000',
            'message': '开票成功',
            'fphm': '00820748268268168425',
            'kprq': '2026-09-30 14:58:10',
            'ewmUrl': 'https://yunshui.test/qr/1',
        }

        self.assertIsNone(self._issue(invoice))

        request = next(request for request in self.gateway.requests if request['interface_code'] == SIMPLE_ISSUE)
        self.assertEqual(request['interface_code'], SIMPLE_ISSUE)
        payload = request['inner']
        self.assertEqual(payload['invoiceKind'], '82')
        self.assertEqual(payload['invoiceType'], '1')
        self.assertEqual(payload['deliverType'], '0')
        self.assertEqual(payload['payerRegisterNo'], self.partner_a.vat)
        self.assertEqual(payload['invoiceItems'][0]['itemNo'], '1010101010000000000')
        self.assertEqual(request['outer']['zipCode'], '0')
        self.assertNotIn('payerBank', payload)
        self.assertNotIn('sfzsgmfyhzh', payload)

    def test_buyer_bank_and_address_are_sent_and_shown(self):
        self.partner_a.write({
            'street': '上海市浦东新区',
            'phone': '+86 138 0000 0000',
            'country_id': self.env.ref('base.cn').id,
            'bank_ids': [Command.create({'bank_name': '中国工商银行上海分行', 'account_number': '6222020200001234567'})],
        })
        invoice = self._post_invoice()

        payload = invoice._l10n_cn_edi_prepare_issue_payload(invoice._l10n_cn_edi_get_document('fapiao'))

        self.assertEqual(payload['payerAddress'], '上海市浦东新区')
        self.assertEqual(payload['payerPhone'], '13800000000')
        self.assertEqual(payload['payerBank'], '中国工商银行上海分行')
        self.assertEqual(payload['payerBankaccount'], '6222020200001234567')
        self.assertEqual(payload['sfzsgmfyhzh'], 'Y')
        self.assertEqual(payload['sfzsgmfdzdh'], 'Y')

    def test_default_drawer_is_not_sent_as_provider_account(self):
        invoice = self._post_invoice()
        doc = invoice._l10n_cn_edi_get_document('fapiao')
        self.company.l10n_cn_edi_drawer = False
        self.assertNotIn('invoicer', invoice._l10n_cn_edi_prepare_issue_payload(doc))
        self.company.l10n_cn_edi_drawer = 'Configured Drawer'
        self.assertEqual(invoice._l10n_cn_edi_prepare_issue_payload(doc)['invoicer'], 'Configured Drawer')

    def test_query_pending_then_issued(self):
        invoice = self._post_invoice()
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '1000', 'message': '提交成功'}
        queue = [
            {'code': '1002', 'message': '开票中'},
            {
                'code': '1000',
                'message': '开票成功',
                'fphm': '0082X',
                'kprq': '2026-09-30 14:58:10',
            },
        ]

        def query_handler(_payload):
            return queue.pop(0) if len(queue) > 1 else queue[0]

        self.gateway.handlers[QUERY_RESULT] = query_handler

        self.assertIsNone(self._issue(invoice))
        self.assertEqual(invoice.l10n_cn_edi_state, 'issued')
        self.assertEqual(invoice.l10n_cn_edi_fapiao_no, '0082X')

    def test_issued_fapiao_keeps_its_links_and_xml(self):
        invoice = self._post_invoice()
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '1000', 'message': '提交成功'}
        self.gateway.handlers[QUERY_RESULT] = {
            'code': '1000',
            'message': '开票成功',
            'fphm': '00820748268268168425',
            'kprq': '2026-09-30 14:58:10',
            'pdfUrl': 'https://digi.51fapiao.cn/v/pdf',
            'ofdUrl': 'http://digi.51fapiao.cn/v/ofd',
        }
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('dzfp_00820748268268168425.xml', '<EInvoice/>')
        self.gateway.handlers[DOWNLOAD_INVOICE] = {'code': '1000', 'message': 'ok', 'file': b64encode(archive.getvalue()).decode()}

        self._issue(invoice)

        doc = self._fapiao(invoice)
        self.assertEqual(doc.pdf_url, 'https://digi.51fapiao.cn/v/pdf')
        self.assertFalse(doc.ofd_url, "only https links are kept")
        self.assertEqual(doc.xml_id.raw.content, b'<EInvoice/>')
        self.assertEqual(invoice.l10n_cn_edi_fapiao_date, datetime(2026, 9, 30, 6, 58, 10))
        download = next(request for request in self.gateway.requests if request['interface_code'] == DOWNLOAD_INVOICE)
        self.assertEqual(download['inner']['fileType'], '3')

    def test_malformed_xml_does_not_lose_issued_state(self):
        invoice = self._post_invoice()
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '1000', 'message': '提交成功'}
        self.gateway.handlers[QUERY_RESULT] = {
            'code': '1000',
            'message': '开票成功',
            'fphm': '00820748268268168425',
            'kprq': '2026-09-30 14:58:10',
        }
        self.gateway.handlers[DOWNLOAD_INVOICE] = {'code': '1000', 'message': 'ok', 'file': b64encode(b'not a zip').decode()}

        with self.assertLogs(CLIENT, 'WARNING'):
            self._issue(invoice)

        self.assertEqual(invoice.l10n_cn_edi_state, 'issued')
        self.assertEqual(invoice.l10n_cn_edi_fapiao_no, '00820748268268168425')
        self.assertFalse(self._fapiao(invoice).xml_id)

    def test_get_session_state_mapping(self):
        client = self.company._l10n_cn_edi_get_client()
        self.assertEqual(client.get_session_state(), 'ok')
        self.assertEqual(self.gateway.requests[-1]['inner']['cxbz'], '1')
        self.gateway.handlers[GET_CREDIT_LINE] = {'_outer_code': '1101', '_outer_msg': '需重新登陆'}
        self.assertEqual(client.get_session_state(), 'login')
        self.gateway.handlers[GET_CREDIT_LINE] = {'_outer_code': '1102', '_outer_msg': '需扫二维码'}
        self.assertEqual(client.get_session_state(), 'verify')
        self.gateway.handlers[GET_CREDIT_LINE] = {'_outer_code': '9999', '_outer_msg': '未查到纳税人信息'}
        with self.assertRaisesRegex(UserError, 'protocol error 9999'):
            client.get_session_state()
        self.gateway.handlers[GET_CREDIT_LINE] = {'code': '1000', 'message': '查询成功'}
        with self.assertRaisesRegex(UserError, 'could not confirm tax-bureau session status'):
            client.get_session_state()

    def test_special_vat_treatment_is_rejected(self):
        invoice = self._post_invoice()
        invoice.invoice_line_ids.tax_ids.l10n_cn_reduced_tax_code = '01'

        self.assertRegex('\n'.join(invoice._l10n_cn_edi_check_invoice()), 'does not support special VAT treatment')

    def test_tax_rate_outside_the_spec_set_is_rejected(self):
        for rate, accepted in ((0.0, True), (1.0, True), (13.0, True), (17.0, True), (2.0, False), (13.5, False)):
            tax = self.env['account.tax'].create({
                'name': f'VAT {rate}',
                'amount_type': 'percent',
                'amount': rate,
                'type_tax_use': 'sale',
                'company_id': self.company.id,
            })
            invoice = self.init_invoice('out_invoice', partner=self.partner_a, products=self.product_a, taxes=tax)
            with self.subTest(rate=rate):
                if accepted:
                    self.assertEqual(invoice._l10n_cn_edi_prepare_lines()[0]['taxRate'], f'{rate / 100:g}')
                else:
                    self.assertRegex('\n'.join(invoice._l10n_cn_edi_check_invoice()), 'does not accept a .* tax rate')

    def test_duplicate_order_is_reconciled_via_query(self):
        invoice = self._post_invoice()
        payload = invoice._l10n_cn_edi_prepare_issue_payload(invoice._l10n_cn_edi_get_document('fapiao'))
        self.gateway.handlers[SIMPLE_ISSUE] = {
            '_outer_code': '9994',
            '_outer_msg': 'duplicate',
            'code': '9994',
            'message': 'duplicate',
        }
        self.gateway.handlers[QUERY_RESULT] = {'code': '1000', 'message': 'ok'}

        result = self.company._l10n_cn_edi_get_client().issue(payload)

        self.assertEqual(result['state'], 'sent')
        self.assertNotIn('ele.invoice.retry', [request['interface_code'] for request in self.gateway.requests])

    def test_duplicate_order_without_issued_state_fails_reconcile(self):
        invoice = self._post_invoice()
        payload = invoice._l10n_cn_edi_prepare_issue_payload(invoice._l10n_cn_edi_get_document('fapiao'))
        self.gateway.handlers[SIMPLE_ISSUE] = {
            '_outer_code': '9994',
            '_outer_msg': 'duplicate',
            'code': '9994',
            'message': 'duplicate',
        }
        self.gateway.handlers[QUERY_RESULT] = {'code': '2001', 'message': 'failed'}

        result = self.company._l10n_cn_edi_get_client().issue(payload)

        self.assertEqual(result['state'], 'failed')
        self.assertTrue(result['new_serial'])

    def test_issue_pending_code_is_not_accepted(self):
        invoice = self._post_invoice()
        payload = invoice._l10n_cn_edi_prepare_issue_payload(invoice._l10n_cn_edi_get_document('fapiao'))
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '1002', 'message': '开票中'}

        result = self.company._l10n_cn_edi_get_client().issue(payload)

        self.assertEqual(result['state'], 'failed')

    def test_issued_result_reads_no_totals(self):
        result = self.company._l10n_cn_edi_get_client()._issued_result({
            'fphm': '0082X',
            'kprq': '2026-09-30 14:58:10',
            'sumPrice': '1.00',
            'sumTax': '0.06',
        })

        self.assertFalse({'amount_total', 'amount_untaxed', 'amount_tax'} & result.keys())

    def _sent_invoice(self):
        invoice = self._post_invoice()
        self._sent_fapiao(invoice, 'BLUE_1_1_X')
        return invoice

    def test_definitive_query_failure_asks_for_new_serial(self):
        invoice = self._sent_invoice()
        client = self.company._l10n_cn_edi_get_client()
        self.gateway.handlers[QUERY_RESULT] = {'code': '2001', 'message': '开票失败'}

        self.assertEqual(client.query_invoice(self._fapiao(invoice), just_submitted=True), {'state': 'sent'})
        result = client.query_invoice(self._fapiao(invoice))
        self.assertEqual(result['state'], 'failed')
        self.assertTrue(result['new_serial'])

        self.env['account.move']._cron_l10n_cn_edi_poll_invoices()
        self.assertEqual(invoice.l10n_cn_edi_state, 'failed')
        self.assertEqual(self._fapiao(invoice).state, 'cancelled')

    def test_query_session_codes_are_not_failures(self):
        invoice = self._sent_invoice()
        client = self.company._l10n_cn_edi_get_client()
        for response, error in (
            ({'code': '1101', 'message': '需重新登陆'}, 'requires tax-bureau login'),
            ({'_outer_code': '1101', '_outer_msg': '需重新登陆'}, 'requires tax-bureau login'),
            ({'code': '1102', 'message': '需扫二维码'}, '实人认证'),
            ({'_outer_code': '1102', '_outer_msg': '需扫二维码'}, '实人认证'),
        ):
            self.gateway.handlers[QUERY_RESULT] = response
            with self.assertRaisesRegex(UserError, error):
                client.query_invoice(self._fapiao(invoice))
        self.gateway.handlers[QUERY_RESULT] = {'_outer_code': '1001', '_outer_msg': '解密异常'}
        with self.assertRaisesRegex(UserError, 'protocol error 1001'):
            client.query_invoice(self._fapiao(invoice))

    def test_relogin_code_on_issue_forces_next_login(self):
        invoice = self._post_invoice()
        client = self.company._l10n_cn_edi_get_client()
        for response in ({'code': '3203', 'message': '需强制重新登录'}, {'_outer_code': '3203', '_outer_msg': '需强制重新登录'}):
            self.company.sudo().l10n_cn_edi_yunshui_relogin = False
            self.gateway.handlers[SIMPLE_ISSUE] = response
            self.assertIn('requires tax-bureau login', invoice._l10n_cn_edi_submit_invoice(client))
            self.assertNotEqual(invoice.l10n_cn_edi_state, 'failed')
            self.assertTrue(self.company.sudo().l10n_cn_edi_yunshui_relogin)

        logins = []
        self.gateway.handlers[LOGIN] = lambda payload: logins.append(payload) or {'step_code': '2', 'data': ['09']}
        action = self.company._l10n_cn_edi_action_login()
        self.assertEqual(logins[-1]['reloginflag'], 'true')
        self.assertTrue(self.company.sudo().l10n_cn_edi_yunshui_relogin)

        wizard = self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id'])
        self.gateway.handlers[LOGIN] = lambda payload: logins.append(payload) or {'step_code': '0'}
        wizard.zrrlx = '09'
        wizard.action_select_role()
        self.assertNotIn('reloginflag', logins[-1])
        self.assertFalse(self.company.sudo().l10n_cn_edi_yunshui_relogin)

        self.company._l10n_cn_edi_action_login()
        self.assertNotIn('reloginflag', logins[-1])

    def test_relogin_code_on_query_survives_the_poll_cron(self):
        invoice = self._sent_invoice()
        self.gateway.handlers[QUERY_RESULT] = {'_outer_code': '3203', '_outer_msg': '需强制重新登录'}

        with self.assertLogs(CLIENT, 'WARNING'):
            self.env['account.move']._cron_l10n_cn_edi_poll_invoices()

        self.assertEqual(invoice.l10n_cn_edi_state, 'sent')
        self.assertTrue(self.company.sudo().l10n_cn_edi_yunshui_relogin)

    def test_unreadable_responses_are_user_errors(self):
        client = self.company._l10n_cn_edi_get_client()
        for raw in (
            MockResponse(content=b'<html>busy</html>'),
            MockResponse(content=b'\xff\xfe'),
            MockResponse(body={'code': '1000', 'msg': ''}),
            MockResponse(body={'code': '1000', 'datagram': 'x', 'access_token': 'abc'}),
        ):
            self.gateway.raw_response = raw
            with self.assertRaisesRegex(UserError, 'could not read'), self.assertLogs(CLIENT, 'WARNING'):
                client.get_session_state()

    def test_response_body_is_capped(self):
        self.gateway.raw_response = MockResponse(content=b'{"code": "1000", "datagram": "' + b'A' * 2048 + b'"}')
        with patch(f'{CLIENT}.MAX_RESPONSE_BYTES', 1024), self.assertRaisesRegex(UserError, 'could not read'), self.assertLogs(CLIENT, 'WARNING'):
            self.company._l10n_cn_edi_get_client().get_session_state()

    def test_response_signature_is_ignored(self):
        self.company.l10n_cn_edi_yunshui_gateway = 'prod'
        self.gateway.bad_signature = True
        self.assertEqual(self.company._l10n_cn_edi_get_client().get_session_state(), 'ok')

    def test_network_failure_is_user_error(self):
        self.gateway.unreachable = True
        with self.assertRaisesRegex(UserError, 'Yunshui did not answer'), self.assertLogs(CLIENT, 'WARNING'):
            self.company._l10n_cn_edi_get_client().test_connection()
