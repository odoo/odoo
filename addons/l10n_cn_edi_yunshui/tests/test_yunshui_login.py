# Part of Odoo. See LICENSE file for full copyright and licensing details.
from base64 import b64decode
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from .common import HOST, L10nCnEdiYunshuiTestCommon, MockResponse, MockYunshuiGateway


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestYunshuiLogin(L10nCnEdiYunshuiTestCommon):

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

    def test_login_action_creates_wizard_and_runs_first_step(self):
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '2', 'data': ['03', '09'], 'message': '请选择责任人'}

        action = self.company._l10n_cn_edi_action_login()

        self.assertEqual(action['res_model'], 'l10n_cn_edi_yunshui.login')
        wizard = self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id'])
        self.assertEqual(wizard.step_code, '2')
        self.assertEqual(wizard.role_options, '03,09')

    def test_login_step_code_0_returns_success_notification(self):
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '0', 'message': '登录成功'}

        action = self.company._l10n_cn_edi_action_login()

        self.assertEqual(action['tag'], 'display_notification')

    def test_sms_code_validation(self):
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '3', 'message': '请输入验证码'}
        action = self.company._l10n_cn_edi_action_login()
        wizard = self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id'])

        wizard.sms_code = 'abc'
        with self.assertRaisesRegex(UserError, 'numeric SMS code'):
            wizard.action_submit_sms()

    def test_qr_status_needs_qrcode_id(self):
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '4', 'message': '请扫码'}
        action = self.company._l10n_cn_edi_action_login()
        wizard = self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id'])

        with self.assertRaisesRegex(UserError, 'Missing QR code id'):
            wizard.action_verify_qr()

    def test_role_must_be_offered_by_bureau(self):
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '2', 'data': ['03'], 'message': '请选择责任人'}
        action = self.company._l10n_cn_edi_action_login()
        wizard = self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id'])
        wizard.zrrlx = '09'

        with self.assertRaisesRegex(UserError, 'role is not offered'):
            wizard.action_select_role()

    def test_qr_payload_is_rendered_as_image(self):
        png_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '4', 'message': '请扫码', 'qrcode': png_b64, 'qrcode_id': 'qr-1'}

        action = self.company._l10n_cn_edi_action_login()
        wizard = self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id'])

        self.assertEqual(bytes(wizard.qrcode_image), b64decode(png_b64))
        self.assertNotIn('qrcode_image_url', wizard._fields)

    def test_qr_poll_preserves_known_qr_values_if_omitted(self):
        png_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '4', 'message': '请扫码', 'qrcode': png_b64, 'qrcode_id': 'qr-2', 'expires_in': 120, 'qrcode_status': '1'}
        action = self.company._l10n_cn_edi_action_login()
        wizard = self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id'])

        self.gateway.handlers['ele.eleLogin'] = {'step_code': '4', 'message': '轮询中'}
        wizard.action_verify_qr()

        self.assertEqual(self.gateway.requests[-1]['inner']['qrcode_id'], 'qr-2')
        self.assertEqual(bytes(wizard.qrcode_image), b64decode(png_b64))
        self.assertEqual(wizard.qrcode_id, 'qr-2')
        self.assertEqual(wizard.qrcode_expires_in, '120')
        self.assertEqual(wizard.qrcode_status, '1')

    def test_verify_state_asks_for_portal_authentication(self):
        self.gateway.handlers['ele.creditLine'] = {'_outer_code': '1102', '_outer_msg': '需扫二维码'}

        with self.assertRaisesRegex(UserError, '实人认证.*Aisino Yunshui portal'):
            self.company._l10n_cn_edi_action_login()
        self.assertNotIn('ele.eleLogin', [request['interface_code'] for request in self.gateway.requests])

    def test_logged_out_session_opens_login(self):
        self.gateway.handlers['ele.creditLine'] = {'_outer_code': '1101', '_outer_msg': '需重新登陆'}
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '0', 'message': '登录成功'}

        action = self.company._l10n_cn_edi_action_login()

        self.assertEqual(action['tag'], 'display_notification')

    def test_login_step_does_not_read_relogin_code(self):
        self.gateway.handlers['ele.eleLogin'] = {'code': '3203', 'step_code': '2', 'data': ['09']}

        action = self.company._l10n_cn_edi_action_login()

        self.assertEqual(self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id']).step_code, '2')

    def test_login_uses_region_code_when_configured(self):
        self.company.l10n_cn_edi_yunshui_region_code = '4403'
        calls = []

        def login_handler(payload):
            calls.append(payload)
            return {'step_code': '0', 'message': '登录成功'}

        self.gateway.handlers['ele.eleLogin'] = login_handler

        self.company._l10n_cn_edi_action_login()

        self.assertEqual(calls[0]['dqbm'], '4403')

    def test_cross_company_wizard_is_rejected(self):
        other = self.env['res.company'].create({
            'name': 'Other Co',
            'vat': '91310115MA1K39423E',
            'l10n_cn_edi_yunshui_identity_code': 'b1492023dcd5368f',
            'l10n_cn_edi_yunshui_platform_code': '101001',
            'l10n_cn_edi_yunshui_gateway': 'test',
        })
        unauthorized = new_test_user(
            self.env,
            login='yunshui_unauthorized',
            groups='account.group_account_invoice',
            company_id=self.company.id,
            company_ids=[(6, 0, (self.company + other).ids)],
        )
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '2', 'message': '请选择责任人'}
        wizard = self.env['l10n_cn_edi_yunshui.login'].with_user(unauthorized).create({'company_id': other.id, 'step_name': 'login'})
        unauthorized.write({'company_ids': [(6, 0, self.company.ids)]})
        self.assertFalse(self.gateway.requests)

        with self.assertRaisesRegex(UserError, 'cannot operate Yunshui login for this company'):
            wizard.with_user(unauthorized).action_restart()
        self.assertFalse(self.gateway.requests)

    def test_wizard_record_rule_blocks_other_invoicing_user(self):
        self.gateway.handlers['ele.eleLogin'] = {'step_code': '2', 'message': '请选择责任人'}
        action = self.company._l10n_cn_edi_action_login()
        wizard = self.env['l10n_cn_edi_yunshui.login'].browse(action['res_id'])
        other_user = new_test_user(
            self.env,
            login='yunshui_other_invoicing_user',
            groups='account.group_account_invoice',
            company_id=self.company.id,
            company_ids=[(6, 0, self.company.ids)],
        )

        with self.assertRaises(AccessError):
            wizard.with_user(other_user).action_restart()
