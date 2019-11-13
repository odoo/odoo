
import requests
import json
import base64
import logging

from odoo.addons.account.tests.common import AccountTestCommon
from odoo.tests import tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', '-standard', 'external')
class TestPingenSend(AccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pingen_url = "https://stage-api.pingen.com/document/upload/token/30fc3947dbea4792eb12548b41ec8117/"
        cls.sample_invoice = cls.create_invoice()
        cls.sample_invoice.partner_id.vat = "BE000000000"
        cls.letter = cls.env['snailmail.letter'].create({
            'partner_id': cls.sample_invoice.partner_id.id,
            'model': 'account.move',
            'res_id': cls.sample_invoice.id,
            'user_id': cls.env.user.id,
            'company_id': cls.sample_invoice.company_id.id,
            'report_template': cls.env.ref('account.account_invoices').id
        })
        cls.data = {
            'data': json.dumps({
                'speed': 1,
                'color': 1,
                'duplex': 0,
                'send': True,
            })
        }

    @classmethod
    def create_invoice(cls):
        """ Create a sample invoice """
        invoice = cls.env['account.move'].with_context(default_type='out_invoice').create({
            'type': 'out_invoice',
            'partner_id': cls.env.ref("base.res_partner_2").id,
            'currency_id': cls.env.ref('base.EUR').id,
            'invoice_date': '2018-12-11',
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.env.ref("product.product_product_4").id,
                'quantity': 1,
                'price_unit': 42,
            })],
        })

        invoice.post()

        return invoice

    def render_and_send(self, report_name):
        self.sample_invoice.company_id.external_report_layout_id = self.env.ref('web.' + report_name)
        self.letter.attachment_id = False

        attachment_id = self.letter.with_context(force_report_rendering=True)._fetch_attachment()

        files = {
            'file': ('pingen_test_%s.pdf' % report_name, base64.b64decode(attachment_id.datas), 'application/pdf'),
        }

        response = requests.post(self.pingen_url, data=self.data, files=files)
        if 400 <= response.status_code <= 599:
            msg = "%(code)s %(side)s Error: %(reason)s for url: %(url)s\n%(body)s" % {
                'code': response.status_code,
                'side': r"%s",
                'reason': response.reason,
                'url': self.pingen_url,
                'body': response.text}
            if response.status_code <= 499:
                raise requests.HTTPError(msg % "Client")
            else:
                _logger.warning(msg % "Server")

    def test_pingen_send_invoice(self):
        # Avoid assets to be unlinked during the test
        # and to reload the registry
        self.registry.enter_test_mode(self.cr)

        self.render_and_send('external_layout_standard')
        self.render_and_send('external_layout_background')
        self.render_and_send('external_layout_boxed')
        self.render_and_send('external_layout_clean')
