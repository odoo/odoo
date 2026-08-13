from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.addons.base.tests.common import BaseUsersCommon


@tagged('post_install', '-at_install')
class TestPortalInvoice(BaseUsersCommon, AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_partner = cls.user_portal.partner_id

    def test_portal_my_invoice_detail_not_his_invoice(self):
        not_his_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        })
        not_his_invoice.action_post()
        url = f'/my/invoices/{not_his_invoice.id}?report_type=pdf&download=True'
        self.authenticate(self.user_portal.login, self.user_portal.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)

    def test_portal_my_invoice_detail_download_pdf(self):
        invoice_with_pdf = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.portal_partner.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        })
        invoice_with_pdf.action_post()
        invoice_with_pdf._generate_and_send()
        self.assertTrue(invoice_with_pdf.invoice_pdf_report_id)

        url = f'/my/invoices/{invoice_with_pdf.id}?report_type=pdf&download=True'
        self.authenticate(self.user_portal.login, self.user_portal.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, invoice_with_pdf.invoice_pdf_report_id.raw)

    def test_portal_my_invoice_detail_download_proforma(self):
        invoice_no_pdf = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.portal_partner.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        })
        invoice_no_pdf.action_post()
        self.assertFalse(invoice_no_pdf.invoice_pdf_report_id)

        url = f'/my/invoices/{invoice_no_pdf.id}?report_type=pdf&download=True'
        self.authenticate(self.user_portal.login, self.user_portal.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("<span>PROFORMA</span>", res.content.decode('utf-8'))
