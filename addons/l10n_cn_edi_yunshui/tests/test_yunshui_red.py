# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import zipfile
from base64 import b64encode
from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import HOST, L10nCnEdiYunshuiTestCommon, MockYunshuiGateway
from odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client import (
    BLUE_LIST,
    H5_DOWNLOAD,
    RED_FORM_DETAIL,
    RED_FORM_INIT,
    RED_FORM_ISSUE,
    RED_FORM_LIST,
    RED_FORM_UPDATE,
)

BLUE_NO = '00820748268268168425'
RED_NO = '00465309071486707222'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestYunshuiRed(L10nCnEdiYunshuiTestCommon):

    def setUp(self):
        super().setUp()
        self.gateway = MockYunshuiGateway(
            self.company.l10n_cn_edi_yunshui_identity_code,
            self.company.l10n_cn_edi_yunshui_platform_code,
        )
        patch('odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client.requests.post', self.gateway).start()
        patch('odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client.HOSTS', {'test': HOST, 'prod': HOST}).start()
        self.addCleanup(patch.stopall)
        # As the sandbox answered on 2026-11-04, cut down.
        self.gateway.handlers[BLUE_LIST] = {'total': 1, 'list': [{
            'fp_hm': BLUE_NO, 'kprq': '2026-11-03 17:56:05', 'sflzfp': 'Y', 'fply_dm': '2', 'gjbq': '1', 'fplx_dm': '82',
            'kpfnsrsbh': self.company.vat, 'ghf_nsrsbh': '',
        }]}
        self.gateway.handlers[RED_FORM_INIT] = {
            'code': 'Y', 'message': '成功', 'lzfphm': BLUE_NO, 'xsfnsrsbh': self.company.vat, 'jshj': 1.06,
            'hzqrxxzt_dm': '01', 'hzqrxxmx_list': [{'xh': 1, 'je': '-1.00', 'sl1': '0.06', 'se': '-0.06'}],
        }
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f'dzfp_{RED_NO}.xml', '<EInvoice/>')
        self.gateway.handlers[H5_DOWNLOAD] = lambda payload: (
            {'wjl': b64encode(archive.getvalue()).decode()} if payload['xzlx'] == '2'
            else {'jfdljUrl': f"https://digi.51fapiao.cn/v/{payload['xzlx']}"}
        )

    def _form(self, state, red_no=None):
        return {
            'code': 'Y', 'uuid': 'a' * 32, 'hzfpxxqrdbh': '67045685257273632319', 'hzqrxxzt_dm': state,
            **({'hzfp_hm': red_no, 'hzkprq': '2026-11-04 11:39:50'} if red_no else {}),
        }

    def _red_form(self, credit_note):
        return credit_note.l10n_cn_edi_document_ids.filtered(lambda doc: doc.kind == 'red_form')

    def test_red_fapiao_issued_at_once_when_the_buyer_need_not_confirm(self):
        credit_note = self._credit_note(reason='01')
        self.gateway.handlers[RED_FORM_ISSUE] = self._form('01', RED_NO)

        credit_note.action_l10n_cn_edi_request_red_form()

        self.assertEqual(
            [request['interface_code'] for request in self.gateway.requests][:3],
            [BLUE_LIST, RED_FORM_INIT, RED_FORM_ISSUE],
        )
        issue = next(request for request in self.gateway.requests if request['interface_code'] == RED_FORM_ISSUE)
        self.assertTrue(issue['url'].endswith('/ele.h5.pass.through'))
        self.assertEqual(issue['headers']['X-KPY-YHM'], self.company.l10n_cn_edi_yunshui_username)
        self.assertEqual(issue['inner']['jshjdx'], '壹圆零陆分')
        self.assertEqual(issue['inner']['xhf_nsrsbh'], self.company.vat)
        self.assertEqual(issue['inner']['chyydm'], '01')
        self.assertEqual(issue['inner']['hzqrxxmxlist'][0]['sl'], '0.06')
        self.assertRecordValues(credit_note, [{
            'l10n_cn_edi_state': 'issued',
            'l10n_cn_edi_fapiao_no': RED_NO,
            'l10n_cn_edi_red_form_number': '67045685257273632319',
            'l10n_cn_edi_red_form_status': 'red_form_confirmed',
        }])
        doc = self._red_form(credit_note)
        self.assertEqual(doc.pdf_url, 'https://digi.51fapiao.cn/v/0')
        self.assertEqual(doc.xml_id.raw.content, b'<EInvoice/>')
        credit_note.action_post()

    def test_red_form_waits_for_the_buyer(self):
        credit_note = self._credit_note(reason='02')
        self.gateway.handlers[RED_FORM_ISSUE] = self._form('02')

        credit_note.action_l10n_cn_edi_request_red_form()

        self.assertEqual(credit_note.l10n_cn_edi_red_form_status, 'red_form_pending')
        self.assertNotEqual(credit_note.l10n_cn_edi_state, 'issued')
        with self.assertRaisesRegex(UserError, 'only once its red fapiao is issued'):
            credit_note.action_post()

        self.gateway.handlers[RED_FORM_DETAIL] = self._form('04', RED_NO)
        self.env['l10n_cn_edi.document']._cron_check_red_form_status()

        self.assertEqual(credit_note.l10n_cn_edi_state, 'issued')
        self.assertEqual(credit_note.l10n_cn_edi_fapiao_no, RED_NO)
        self.assertEqual(self.gateway.requests[-4]['inner'], {'uuid': 'a' * 32, 'xhf_nsrsbh': self.company.vat})

    def test_revoke_a_red_form_the_buyer_has_not_answered(self):
        credit_note = self._credit_note(reason='02')
        self.gateway.handlers[RED_FORM_ISSUE] = self._form('02')
        credit_note.action_l10n_cn_edi_request_red_form()

        credit_note.action_l10n_cn_edi_cancel_red_form()

        self.assertEqual(self.gateway.requests[-1]['interface_code'], RED_FORM_UPDATE)
        self.assertEqual(self.gateway.requests[-1]['inner']['czlx'], '3')
        self.assertRecordValues(self._red_form(credit_note), [{'state': 'cancelled', 'bureau_state': '08'}])

    def test_reversed_fapiao_is_not_offered(self):
        credit_note = self._credit_note(reason='02')
        self.gateway.handlers[BLUE_LIST] = {'total': 0, 'list': []}

        credit_note.action_l10n_cn_edi_request_red_form()

        self.assertEqual(self._red_form(credit_note).state, 'failed')
        self.assertIn('may already be reversed', credit_note.message_ids[0].body)
        self.assertNotIn(RED_FORM_ISSUE, [request['interface_code'] for request in self.gateway.requests])

    def test_red_relogin_code_forces_next_login(self):
        credit_note = self._credit_note(reason='02')
        self.gateway.handlers[BLUE_LIST] = {'_outer_code': '3203', '_outer_msg': '需强制重新登录'}

        credit_note.action_l10n_cn_edi_request_red_form()

        self.assertEqual(self._red_form(credit_note).state, 'failed')
        self.assertTrue(self.company.sudo().l10n_cn_edi_yunshui_relogin)

    def test_red_form_whose_answer_was_lost_is_adopted(self):
        credit_note = self._credit_note(reason='02')
        self.gateway.handlers[BLUE_LIST] = {'total': 0, 'list': []}
        self.gateway.handlers[RED_FORM_LIST] = {'total': 1, 'list': [{**self._form('02'), 'lzfphm': BLUE_NO}]}
        self.gateway.handlers[RED_FORM_DETAIL] = self._form('02')

        credit_note.action_l10n_cn_edi_request_red_form()

        self.assertRecordValues(self._red_form(credit_note), [{'state': 'red_form_pending', 'red_form_uuid': 'a' * 32}])
        self.assertNotIn(RED_FORM_ISSUE, [request['interface_code'] for request in self.gateway.requests])

    def test_inbound_red_forms_are_listed_page_by_page_for_both_sides_once(self):
        rows = {'0': [{**self._form('03'), 'uuid': f'{index:032}', 'lzfphm': BLUE_NO} for index in range(51)]}
        rows['1'] = rows['0'][-1:]
        self.gateway.handlers[RED_FORM_LIST] = lambda payload: {
            'total': len(rows[payload['gxfxz']]),
            'list': rows[payload['gxfxz']][(int(payload['cxym']) - 1) * 50:][:50],
        }

        forms = self.company._l10n_cn_edi_get_client().list_inbound_red_forms(date(2026, 11, 1), date(2026, 11, 4))

        self.assertEqual(len(forms), 51)
        self.assertEqual(
            [(request['inner']['gxfxz'], request['inner']['cxlx'], request['inner']['cxym']) for request in self.gateway.requests],
            [('0', '1', '1'), ('0', '1', '2'), ('1', '1', '1')],
        )
        self.assertEqual(forms[0]['original_fapiao_no'], BLUE_NO)
        self.assertEqual(forms[0]['bureau_state'], '03')

    def test_supplier_red_form_is_answered_as_the_buyer(self):
        bill = self.init_invoice('in_invoice', partner=self.partner_a, products=self.product_a, post=True)
        bill.l10n_cn_edi_fapiao_no = BLUE_NO
        self.gateway.handlers[RED_FORM_LIST] = lambda payload: {
            'total': 1,
            'list': [{**self._form('02'), 'lzfphm': BLUE_NO, 'hzcxje': '-1.00', 'hzcxse': '-0.06'}] if payload['gxfxz'] == '1' else [],
        }

        self.env['l10n_cn_edi.document']._cron_check_red_form_status()
        bill.action_l10n_cn_edi_reject_inbound_red_form()

        self.assertRecordValues(bill.l10n_cn_edi_document_ids, [{'state': 'cancelled', 'amount_untaxed': -1.0}])
        update = self.gateway.requests[-1]
        self.assertEqual(update['interface_code'], RED_FORM_UPDATE)
        self.assertEqual((update['inner']['czlx'], update['inner']['xhf_nsrsbh']), ('2', self.partner_a.vat))
