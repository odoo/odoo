# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import HOST, L10nCnEdiYunshuiTestCommon, MockResponse, MockYunshuiGateway
from odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client import (
    QUERY_RED_FORM,
    QUERY_RESULT,
    SIMPLE_ISSUE,
)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestYunshuiRed(L10nCnEdiYunshuiTestCommon):

    def setUp(self):
        super().setUp()
        self.gateway = MockYunshuiGateway(
            self.company.l10n_cn_edi_yunshui_identity_code,
            self.company.l10n_cn_edi_yunshui_platform_code,
        )
        patch('odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client.requests.post', self.gateway).start()
        patch(
            'odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client.requests.get',
            lambda url, **kwargs: MockResponse(status=404),
        ).start()
        patch('odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client.HOSTS', {'test': HOST, 'prod': HOST}).start()
        self.addCleanup(patch.stopall)

    def test_full_red_uses_simple_issue_invoice_type_2(self):
        credit_note = self._credit_note(reason='01')
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '1000', 'message': '提交成功'}
        self.gateway.handlers[QUERY_RESULT] = {'code': '1002', 'message': '开票中'}

        credit_note.action_l10n_cn_edi_request_red_form()

        request = self.gateway.requests[0]
        self.assertEqual(request['interface_code'], SIMPLE_ISSUE)
        payload = request['inner']
        self.assertEqual(payload['invoiceType'], '2')
        self.assertEqual(payload['originInvoiceNo'], '00820748268268168425')
        self.assertEqual(payload['redReason'], '01')
        self.assertNotIn('invoiceItems', payload)
        self.assertEqual(self._fapiao(credit_note).state, 'sent')
        self.assertEqual(credit_note.l10n_cn_edi_state, 'sent')

    def test_red_poll_issues_the_credit_note(self):
        credit_note = self._credit_note(reason='02')
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '1000', 'message': '提交成功'}
        self.gateway.handlers[QUERY_RESULT] = {'code': '1002', 'message': '开票中'}
        credit_note.action_l10n_cn_edi_request_red_form()

        self.gateway.handlers[QUERY_RESULT] = {
            'code': '1000',
            'message': '开票成功',
            'fphm': '29746948242065126876',
            'kprq': '2026-09-30 14:58:27',
        }
        self.gateway.handlers[QUERY_RED_FORM] = {'code': 'y', 'uuid': 'a' * 32, 'hzfpxxqrdbh': '44030025093000012345'}
        self.env['account.move']._cron_l10n_cn_edi_poll_invoices()

        self.assertEqual(self._fapiao(credit_note).state, 'issued')
        self.assertRecordValues(credit_note, [{
            'l10n_cn_edi_state': 'issued',
            'l10n_cn_edi_fapiao_no': '29746948242065126876',
            'l10n_cn_edi_red_form_number': '44030025093000012345',
            'l10n_cn_edi_red_form_uuid': 'a' * 32,
            'l10n_cn_edi_red_form_status': False,
        }])
        self.assertEqual(self.gateway.requests[-1]['inner'], {'fpqqlsh': self._fapiao(credit_note).serial_no, 'invoiceKind': '82'})

    def test_red_definitive_failure_asks_for_new_serial(self):
        credit_note = self._credit_note(reason='02')
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '1000', 'message': '提交成功'}
        self.gateway.handlers[QUERY_RESULT] = {'code': '1002', 'message': '开票中'}
        credit_note.action_l10n_cn_edi_request_red_form()

        self.gateway.handlers[QUERY_RESULT] = {'code': '2001', 'message': '开票失败'}
        # Past the grace period in which a fresh order may not be known yet.
        self._fapiao(credit_note).sent_date = fields.Datetime.subtract(fields.Datetime.now(), hours=1)
        self.env['account.move']._cron_l10n_cn_edi_poll_invoices()

        self.assertEqual(credit_note.l10n_cn_edi_state, 'failed')
        self.assertEqual(self._fapiao(credit_note).state, 'cancelled')

    def test_red_relogin_code_forces_next_login(self):
        credit_note = self._credit_note(reason='02')
        self.gateway.handlers[SIMPLE_ISSUE] = {'_outer_code': '3203', '_outer_msg': '需强制重新登录'}

        credit_note.action_l10n_cn_edi_request_red_form()

        self.assertNotEqual(credit_note.l10n_cn_edi_state, 'failed')
        self.assertTrue(self.company.sudo().l10n_cn_edi_yunshui_relogin)

    def test_red_failure_returns_provider_message(self):
        credit_note = self._credit_note(reason='04')
        self.gateway.handlers[SIMPLE_ISSUE] = {'code': '2001', 'message': '原发票已全额冲红'}

        credit_note.action_l10n_cn_edi_request_red_form()

        self.assertEqual(self._fapiao(credit_note).state, 'failed')
        self.assertEqual(credit_note.l10n_cn_edi_state, 'failed')

    def test_inbound_listing_is_empty_for_now(self):
        with self.assertRaisesRegex(UserError, 'does not support listing inbound red forms'):
            self.company._l10n_cn_edi_get_client().list_inbound_red_forms(
                date(2026, 9, 1),
                date(2026, 9, 30),
            )
