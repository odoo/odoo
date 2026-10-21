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
            'invoice_line_ids': [Command.create({'price_unit': 100})],
            'attachment_ids': [Command.create({'name': "Attachment", 'mimetype': 'text/plain', 'res_model': 'account.move', 'datas': "test"})],
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
            self.assertEqual(
                zip_file.namelist(),
                self.invoices.invoice_pdf_report_id.mapped('name'),
            )

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
            self.assertEqual(
                zip_file.namelist(),
                self.invoices.invoice_pdf_report_id.mapped('name'),
            )

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
<<<<<<< a896484eeada218dec73d908b2d5ffd844ee05d7

    def test_download_moves_attachments(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        url = f'/account/download_move_attachments/{",".join(map(str, self.invoices.ids))}'
        attachment_names = sorted([doc['filename'] for invoice in self.invoices for doc in invoice._get_invoice_legal_documents_all()])
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        with ZipFile(BytesIO(res.content)) as zip_file:
            file_names = sorted(zip_file.namelist())
            self.assertEqual(file_names, attachment_names)

    def test_download_moves_attachments_with_bills(self):
        bill = self.init_invoice('in_invoice', products=self.product_a, post=True)
        bill.message_main_attachment_id = self.env['ir.attachment'].create({'name': "Attachment", 'mimetype': 'text/plain', 'res_model': 'account.move', 'datas': "test_bill"})
        attachment_names = [bill.message_main_attachment_id.name]
        self.authenticate(self.env.user.login, self.env.user.login)
        url = f'/account/download_move_attachments/{bill.id}'
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        with ZipFile(BytesIO(res.content)) as zip_file:
            file_names = sorted(zip_file.namelist())
            self.assertEqual(file_names, attachment_names)

    def test_download_moves_attachments_with_duplicate_names(self):
        bill_1 = self.init_invoice('in_invoice', products=self.product_a, post=True)
        bill_2 = self.init_invoice('in_invoice', products=self.product_a, post=True)
        bill_3 = self.init_invoice('in_invoice', products=self.product_a, post=True)
        att_name = "Attachment"
        bill_1.message_main_attachment_id = self.env['ir.attachment'].create({'name': att_name, 'mimetype': 'text/plain', 'res_model': 'account.move', 'datas': "test_bill"})
        bill_2.message_main_attachment_id = self.env['ir.attachment'].create({'name': att_name, 'mimetype': 'text/plain', 'res_model': 'account.move', 'datas': "test_bill"})
        bill_3.message_main_attachment_id = self.env['ir.attachment'].create({'name': f"{att_name} (1)", 'mimetype': 'text/plain', 'res_model': 'account.move', 'datas': "test_bill"})
        attachment_names = [att_name, f"{att_name} (1)", f"{att_name} (1) (1)"]
        self.authenticate(self.env.user.login, self.env.user.login)

        url = f'/account/download_move_attachments/{bill_1.id},{bill_2.id},{bill_3.id}'
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        with ZipFile(BytesIO(res.content)) as zip_file:
            file_names = sorted(zip_file.namelist())
            self.assertEqual(file_names, attachment_names)

        att_name = "Attachment.ext"
        bill_1.message_main_attachment_id.name = att_name
        bill_2.message_main_attachment_id.name = att_name
        attachment_names = [f"{att_name.split('.')[0]} (1).{att_name.split('.')[1]}", att_name]

        url = f'/account/download_move_attachments/{bill_1.id},{bill_2.id}'
        res = self.url_open(url)
        with ZipFile(BytesIO(res.content)) as zip_file:
            file_names = sorted(zip_file.namelist())
            self.assertEqual(file_names, attachment_names)
||||||| 5be59d6e7de2e0278b4bb2ead69b492606dff0c2
=======

    def _get_rendering_companies(self, func):
        """ Return the companies of the environments in which the reports are rendered when calling ``func``. """
        IrActionsReport = self.env.registry['ir.actions.report']
        render_qweb_html = IrActionsReport._render_qweb_html
        companies = self.env['res.company']

        def _render_qweb_html(report, *args, **kwargs):
            nonlocal companies
            companies |= report.env.company
            return render_qweb_html(report, *args, **kwargs)

        with patch.object(IrActionsReport, '_render_qweb_html', _render_qweb_html):
            func()
        return companies

    def test_invoice_pdf_proforma_company(self):
        """ The proforma is rendered in the company of the invoice (e.g. for its paper format). """
        other_company = self.setup_other_company()['company']
        invoice = self.env['account.move'].with_company(other_company).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})],
        })
        self.assertNotEqual(self.env.company, other_company)
        companies = self._get_rendering_companies(invoice.with_env(self.env)._get_invoice_pdf_proforma)
        self.assertEqual(companies, other_company)

    def test_invoice_pdf_report_several_companies(self):
        """ Invoices of several companies sent together are each rendered in their company. """
        other_company = self.setup_other_company()['company']
        other_invoice = self.env['account.move'].with_company(other_company).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})],
        })
        other_invoice.action_post()
        invoices = self.invoices[0] + other_invoice
        report = self.env.ref('account.account_invoices')
        invoices_data = {invoice: {'pdf_report': report} for invoice in invoices}
        companies = self._get_rendering_companies(
            lambda: self.env['account.move.send'].with_context(allowed_company_ids=(self.env.company | other_company).ids)._prepare_invoice_pdf_report(invoices_data),
        )
        self.assertEqual(companies, invoices.company_id)
>>>>>>> 70761501dc615d5a8ae10b16b941573807fa8daf
