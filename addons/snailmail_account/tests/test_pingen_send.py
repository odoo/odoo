
import requests
import json
import base64

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged

@tagged('post_install', '-at_install', '-standard', 'external')
class TestPingenSend(AccountingTestCase):

    def setUp(self):
        super(TestPingenSend, self).setUp()
        self.pingen_url = "https://stage-api.pingen.com/document/upload/token/30fc3947dbea4792eb12548b41ec8117/"
        self.sample_invoice = self.create_invoice()
        self.sample_invoice.partner_id.vat = "BE000000000"
        self.letter = self.env['snailmail.letter'].create({
            'partner_id': self.sample_invoice.partner_id.id,
            'model': 'account.invoice',
            'res_id': self.sample_invoice.id,
            'user_id': self.env.user.id,
            'company_id': self.sample_invoice.company_id.id,
            'report_template': self.env.ref('account.account_invoices').id
        })
        self.data = {
            'data': json.dumps({
                'speed': 1,
                'color': 2,
                'duplex': 0,
                'send': True,
            })
        }

    def create_invoice(self):
        """ Create a sample invoice """
        currency = self.env.ref('base.EUR')
        partner_agrolait = self.env.ref("base.res_partner_2")
        product = self.env.ref("product.product_product_4")

        account_receivable = self.env['account.account'].create({
            'code': 'TESTPINGEN1',
            'name': 'Test Receivable Account',
            'user_type_id': self.env.ref('account.data_account_type_receivable').id,
            'reconcile': True
        })
        account_income = self.env['account.account'].create({
            'code': 'TESTPINGEN2',
            'name': 'Test Account',
            'user_type_id': self.env.ref('account.data_account_type_direct_costs').id
        })

        invoice = self.env['account.invoice'].create({
            'partner_id': partner_agrolait.id,
            'currency_id': currency.id,
            'name': 'invoice to client',
            'account_id': account_receivable.id,
            'type': 'out_invoice',
            'date_invoice': '2018-12-11',
        })

        self.env['account.invoice.line'].create({
            'product_id': product.id,
            'quantity': 1,
            'price_unit': 42,
            'invoice_id': invoice.id,
            'name': 'something',
            'account_id': account_income.id,
        })

        invoice.action_invoice_open()

        return invoice

    def render_and_send(self, report_name):
        self.sample_invoice.company_id.external_report_layout_id = self.env.ref('web.' + report_name)
        self.letter.attachment_id = False
        attachment_id = self.letter.with_context(force_report_rendering=True)._fetch_attachment()

        files = {
            'file': ('pingen_test_%s.pdf' % report_name, base64.b64decode(attachment_id.datas), 'application/pdf'),
        }

        response = requests.post(self.pingen_url, data=self.data, files=files)

        try:
            response.raise_for_status()
        except:
            return False

        return True

    def test_pingen_send_invoice(self):
        self.assertTrue(self.render_and_send('external_layout_standard'))
        self.assertTrue(self.render_and_send('external_layout_background'))
        self.assertTrue(self.render_and_send('external_layout_boxed'))
        self.assertTrue(self.render_and_send('external_layout_clean'))
