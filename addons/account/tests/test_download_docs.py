from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestDownloadDocs(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        invoice_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        })
        invoice_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [Command.create({'price_unit': 200})]
        })
        cls.invoices = invoice_1 + invoice_2
        cls.invoices.action_post()
        cls.invoices._generate_and_send()
        assert invoice_1.invoice_pdf_report_id and invoice_2.invoice_pdf_report_id

    def test_download_invoice_attachments_not_auth(self):
        url = f'/account/download_invoice_attachments/{",".join(map(str, self.invoices.invoice_pdf_report_id.ids))}'
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(
            'oe_login_form',
            res.content.decode('utf-8'),
            'When not authenticated, the download is not possible.'
        )

    def test_download_invoice_attachments_one(self):
        attachment = self.invoices[0].invoice_pdf_report_id
        url = f'/account/download_invoice_attachments/{attachment.id}'
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, attachment.raw)

    def test_download_invoice_attachments_multiple(self):
        attachments = self.invoices.invoice_pdf_report_id
        url = f'/account/download_invoice_attachments/{",".join(map(str, attachments.ids))}'
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        with ZipFile(BytesIO(res.content)) as zip_file:
            self.assertEqual(len(zip_file.filelist), 2)
            self.assertTrue(zip_file.NameToInfo.get(self.invoices[0].invoice_pdf_report_id.name))
            self.assertTrue(zip_file.NameToInfo.get(self.invoices[1].invoice_pdf_report_id.name))

    def test_download_invoice_documents_filetype_one(self):
        url = f'/account/download_invoice_documents/{self.invoices[0].id}/pdf'
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, self.invoices[0].invoice_pdf_report_id.raw)

    def test_download_invoice_documents_filetype_multiple(self):
        url = f'/account/download_invoice_documents/{",".join(map(str, self.invoices.ids))}/pdf'
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        with ZipFile(BytesIO(res.content)) as zip_file:
            self.assertEqual(len(zip_file.filelist), 2)
            self.assertTrue(zip_file.NameToInfo.get(self.invoices[0].invoice_pdf_report_id.name))
            self.assertTrue(zip_file.NameToInfo.get(self.invoices[1].invoice_pdf_report_id.name))

    def test_download_invoice_documents_filetype_all(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        url = f'/account/download_invoice_documents/{",".join(map(str, self.invoices.ids))}/all'
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        with ZipFile(BytesIO(res.content)) as zip_file:
            file_names = zip_file.namelist()
            self.assertEqual(len(file_names), 2)
            self.assertTrue(self.invoices[0].invoice_pdf_report_id.name in file_names)
            self.assertTrue(self.invoices[1].invoice_pdf_report_id.name in file_names)

    def test_invoice_pdf_proforma_company(self):
        """ The proforma is rendered in the company of the invoice (e.g. for its paper format). """
        other_company = self.setup_other_company()['company']
        invoice = self.env['account.move'].with_company(other_company).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})],
        })
        self.assertNotEqual(self.env.company, other_company)

        IrActionsReport = self.env.registry['ir.actions.report']
        pre_render_qweb_pdf = IrActionsReport._pre_render_qweb_pdf
        companies = []

        def _pre_render_qweb_pdf(report, *args, **kwargs):
            companies.append(report.env.company)
            return pre_render_qweb_pdf(report, *args, **kwargs)

        with patch.object(IrActionsReport, '_pre_render_qweb_pdf', _pre_render_qweb_pdf):
            invoice.with_env(self.env)._get_invoice_pdf_proforma()
        self.assertEqual(companies, [other_company])
