# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from unittest.mock import patch

import requests

from odoo import fields

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_cn_edi_yunshui.crypto import sm4_envelope
from odoo.addons.l10n_cn_edi_yunshui.tools.yunshui_client import YunshuiClient

HOST = 'https://llys.51fapiao.cn/openapi'


class MockResponse:

    def __init__(self, body=None, status=200, content=b''):
        self.status_code = status
        self.content = content if body is None else json.dumps(body, ensure_ascii=False).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=1):
        for index in range(0, len(self.content), chunk_size):
            yield self.content[index:index + chunk_size]


class MockYunshuiGateway:

    def __init__(self, identity_code, platform_code):
        self.identity_code = identity_code
        self.platform_code = platform_code
        self.handlers = {'ele.creditLine': {'sysxed': '99.00', 'ysysxed': '1.00', 'zsxed': '100.00'}}
        self.requests = []
        self.unreachable = False
        self.bad_signature = False
        self.raw_response = None

    def __call__(self, url, data=None, headers=None, timeout=None, stream=False):
        if self.unreachable:
            error = "DNS failure"
            raise requests.ConnectionError(error)
        request_outer = json.loads((data or b'').decode('utf-8'))
        interface_code = request_outer['interfaceCode']
        request_inner = sm4_envelope.verify_and_decrypt(
            dict(request_outer, code='1000'),
            self.identity_code,
            self.platform_code,
        )
        self.requests.append({
            'url': url,
            'interface_code': interface_code,
            'outer': request_outer,
            'inner': request_inner,
        })
        if self.raw_response is not None:
            return self.raw_response
        handler = self.handlers.get(interface_code)
        response_inner = handler(request_inner) if callable(handler) else handler
        if response_inner is None:
            response_inner = {'code': '1000', 'message': 'ok'}
        outer_code = '1000'
        outer_msg = ''
        if isinstance(response_inner, dict):
            outer_code = str(response_inner.pop('_outer_code', outer_code))
            outer_msg = response_inner.pop('_outer_msg', outer_msg)
        response_outer = sm4_envelope.build_response(
            interface_code,
            response_inner,
            self.identity_code,
            self.platform_code,
            code=outer_code,
            msg=outer_msg,
        )
        if outer_code != '1000':
            # On failure the datagram is an empty node and the signature an echo of the request's.
            response_outer.update(datagram='', signature=request_outer['signature'])
        if self.bad_signature:
            response_outer['signature'] = 'BAD' + response_outer['signature'][3:]
        return MockResponse(response_outer)


class L10nCnEdiYunshuiTestCommon(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('cn')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.company.write({
            'vat': '91310115MA1K39423D',
            'l10n_cn_edi_yunshui_identity_code': 'b1492023dcd5368e',
            'l10n_cn_edi_yunshui_platform_code': '101000',
            'l10n_cn_edi_yunshui_gateway': 'test',
            'l10n_cn_edi_yunshui_username': 'demo_user',
            'l10n_cn_edi_yunshui_password': 'demo_pass',
        })
        cls.partner_a.write({'country_id': cls.env.ref('base.cn').id, 'vat': '91330106MA2B2ABCDN'})
        tax_category = cls.env['l10n_cn_edi.tax.category'].sudo().create({'name': 'Test', 'code': '1010101010000000000'})
        (cls.product_a + cls.product_b).product_tmpl_id.l10n_cn_tax_category_id = tax_category

    def _issue(self, invoice):
        return self.env['account.move.send']._l10n_cn_edi_issue_invoices(invoice).get(invoice)

    def setUp(self):
        super().setUp()
        patch.object(YunshuiClient, 'wait', lambda client, seconds: None).start()
        # Outside a cron run, the crons' progress commits would commit the test transaction.
        patch.object(self.env.registry['ir.cron'], '_commit_progress', return_value=float('inf')).start()
        self.addCleanup(patch.stopall)

    def _fapiao(self, move):
        """Return the latest fapiao document of ``move``."""
        return move.l10n_cn_edi_document_ids.filtered(lambda doc: doc.kind == 'fapiao').sorted('id', reverse=True)[:1]

    def _sent_fapiao(self, move, serial_no):
        """Return a fapiao document of ``move`` the provider accepted an hour ago and still has to issue."""
        move.l10n_cn_edi_state = 'sent'
        return self.env['l10n_cn_edi.document'].create({
            'move_id': move.id,
            'kind': 'fapiao',
            'state': 'sent',
            'serial_no': serial_no,
            'sent_date': fields.Datetime.subtract(fields.Datetime.now(), hours=1),
        })

    def _post_invoice(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, products=self.product_a, taxes=self.tax_sale_a)
        invoice.action_post()
        return invoice

    def _credit_note(self, reason='02'):
        invoice = self._post_invoice()
        invoice.sudo().write({'l10n_cn_edi_state': 'issued', 'l10n_cn_edi_fapiao_no': '00820748268268168425'})
        wizard = self.env['account.move.reversal'].with_context(active_ids=invoice.ids, active_model='account.move').create({
            'journal_id': invoice.journal_id.id,
            'reason': 'placeholder',
            'l10n_cn_edi_red_form_reason': reason,
        })
        wizard.reverse_moves()
        return wizard.new_move_ids


class FakeClient:
    """A YunshuiClient that answers from ``responses`` and records every call in ``calls``."""

    result_delays = ()

    def __init__(self, company, responses):
        self.company = company
        self.responses = responses
        self.calls = []

    def _answer(self, method, *args):
        self.calls.append((method, args))
        response = self.responses.get(method)
        if isinstance(response, Exception):
            raise response
        return response() if callable(response) else response

    def ensure_ready(self):
        return self._answer('ensure_ready')

    def get_session_state(self):
        return self._answer('get_session_state') or 'ok'

    def issue_invoice(self, values):
        return self._answer('issue_invoice', values)

    def issue_direct_red(self, values):
        return self._answer('issue_direct_red', values)

    def wait(self, seconds):
        self.calls.append(('wait', (seconds,)))

    def query_invoice(self, document, just_submitted=False):
        return self._answer('query_invoice', document, just_submitted)

    def query_red_form(self, document):
        return self._answer('query_red_form', document)

    def operate_red_form(self, document, action):
        return self._answer('operate_red_form', document, action)

    def list_inbound_red_forms(self, date_from, date_to):
        return self._answer('list_inbound_red_forms', date_from, date_to) or []


class L10nCnEdiTestCommon(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('cn')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].vat = '91310115MA1K39423D'
        cls.partner_a.country_id = cls.env.ref('base.cn')
        tax_category = cls.env['l10n_cn_edi.tax.category'].sudo().create({'name': 'Test', 'code': '1010101010000000000'})
        (cls.product_a + cls.product_b).product_tmpl_id.l10n_cn_tax_category_id = tax_category

    def setUp(self):
        super().setUp()
        self.responses = {}
        self.client = FakeClient(self.company_data['company'], self.responses)
        Company = self.env.registry['res.company']
        patch.object(Company, '_l10n_cn_edi_is_ready', lambda company: True).start()
        patch.object(Company, '_l10n_cn_edi_get_client', lambda company: self.client).start()
        # Outside a cron run, the crons' progress commits would commit the test transaction.
        self.commit_progress = patch.object(self.env.registry['ir.cron'], '_commit_progress', return_value=float('inf')).start()
        self.addCleanup(patch.stopall)

    def _fapiao(self, move):
        """Return the latest fapiao document of ``move``."""
        return move.l10n_cn_edi_document_ids.filtered(lambda doc: doc.kind == 'fapiao').sorted('id', reverse=True)[:1]

    def _set_sent(self, moves):
        """Put ``moves`` where the provider accepted their fapiao and still has to issue it."""
        for move in moves:
            move._l10n_cn_edi_get_document('fapiao')._l10n_cn_edi_set_sent(self.client)

    def _issue(self, invoice):
        """Issue through the send flow; return the invoice's error, or None."""
        return self.env['account.move.send']._l10n_cn_edi_issue_invoices(invoice).get(invoice)

    def _create_posted_invoice(self, fapiao_no=None):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, products=self.product_a, taxes=self.tax_sale_a)
        invoice.action_post()
        if fapiao_no:
            invoice.l10n_cn_edi_fapiao_no = fapiao_no
        return invoice

    def _reverse(self, invoice, reason='02'):
        wizard = invoice.env['account.move.reversal'].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
        ).create({
            'journal_id': invoice.journal_id.id,
            'reason': 'placeholder',
            'l10n_cn_edi_red_form_reason': reason,
        })
        wizard.reverse_moves()
        return wizard.new_move_ids
