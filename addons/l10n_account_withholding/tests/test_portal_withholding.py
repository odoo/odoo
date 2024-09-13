# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import zipfile

from odoo import Command, http
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.addons.base.tests.common import BaseUsersCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPortalWithholding(BaseUsersCommon, AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_partner = cls.user_portal.partner_id
        # Prepare an empty pdf file to test upload and download.
        cls.pdf_file = b'this is a pdf, trust me'

    def test_withholding_tax_upload_document(self):
        """
        Test uploading a file using the controller as a portal user would do.
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.portal_partner.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        })
        invoice.action_post()

        # In the portal, this token is available.
        invoice_access_token = invoice._portal_ensure_token()

        self.authenticate(self.user_portal.login, self.user_portal.login)
        res = self.url_open(
            url='/my/invoices/upload_withholding_certificate',
            data={
                'name': 'test.pdf',
                'thread_id': invoice.id,
                'thread_model': 'account.move',
                'access_token': invoice_access_token,
                'csrf_token': http.Request.csrf_token(self)
            },
            files=[('file', ('test.pdf', self.pdf_file, 'application/pdf'))],
        )
        self.assertEqual(res.text, 'ok')
        self.assertTrue(invoice.l10n_account_withholding_certificate_ids)
        self.assertEqual(invoice.l10n_account_withholding_certificate_ids.name, 'test.pdf')

    def test_withholding_tax_download_document(self):
        """
        A user will upload a file, which will then be downloaded by the accountant.
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.portal_partner.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        })
        invoice.action_post()

        # In the portal, this token is available.
        invoice_access_token = invoice._portal_ensure_token()

        self.authenticate(self.user_portal.login, self.user_portal.login)
        self.url_open(
            url='/my/invoices/upload_withholding_certificate',
            data={
                'name': 'test.pdf',
                'thread_id': invoice.id,
                'thread_model': 'account.move',
                'access_token': invoice_access_token,
                'csrf_token': http.Request.csrf_token(self)
            },
            files=[('file', ('test.pdf', self.pdf_file, 'application/pdf'))],
        )

        # File uploaded, we now download it as an internal user.
        self.authenticate(self.env.user.login, self.env.user.login)
        action = invoice.action_download_withholding_certificates()
        result = self.url_open(url=action['url'])
        # Check that we do get the expected file name
        self.assertRegex(result.headers.get('Content-Disposition', ''), rf"{invoice.name.replace('/', '_')}\.pdf")
        self.assertEqual(result.content, self.pdf_file)

    def test_withholding_tax_download_document_batch(self):
        """
        Same behavior as previous test, but we download the certificate from two invoices at once.
        """
        invoices = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.portal_partner.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        }, {
            'move_type': 'out_invoice',
            'partner_id': self.portal_partner.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        }])
        invoices.action_post()

        self.authenticate(self.user_portal.login, self.user_portal.login)
        for i, invoice in enumerate(invoices):
            self.url_open(
                url='/my/invoices/upload_withholding_certificate',
                data={
                    'name': f'test_{i}.pdf',
                    'thread_id': invoice.id,
                    'thread_model': 'account.move',
                    'access_token': invoice._portal_ensure_token(),
                    'csrf_token': http.Request.csrf_token(self)
                },
                files=[('file', (f'test_{i}.pdf', self.pdf_file, 'application/pdf'))],
            )

        self.authenticate(self.env.user.login, self.env.user.login)
        action = invoices.action_download_withholding_certificates()
        result = self.url_open(url=action['url'])
        self.assertRegex(result.headers.get('Content-Disposition', ''), r'invoices_withholding_certs\.zip')
        # Ensure that the zip contains two files.
        with zipfile.ZipFile(io.BytesIO(result.content)) as downloaded_zip:
            file_count = len(downloaded_zip.filelist)
        self.assertEqual(file_count, 2)

    def test_withholding_tax_upload_multiple_documents(self):
        """ Ensure that uploading multiple certificate to a single invoice works as expected. """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.portal_partner.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        })
        invoice.action_post()

        # In the portal, this token is available.
        invoice_access_token = invoice._portal_ensure_token()

        self.authenticate(self.user_portal.login, self.user_portal.login)
        for file in ['tesT.pdf', 'test.pdf']:
            res = self.url_open(
                url='/my/invoices/upload_withholding_certificate',
                data={
                    'name': file,
                    'thread_id': invoice.id,
                    'thread_model': 'account.move',
                    'access_token': invoice_access_token,
                    'csrf_token': http.Request.csrf_token(self)
                },
                files=[('file', (file, self.pdf_file, 'application/pdf'))],
            )
            self.assertEqual(res.text, 'ok')

        self.assertEqual(len(invoice.l10n_account_withholding_certificate_ids), 2)

    def test_withholding_tax_download_multiple_documents(self):
        """
        Test that downloading multiple documents from a single invoice works as expected
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.portal_partner.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})]
        })
        invoice.action_post()

        # In the portal, this token is available.
        invoice_access_token = invoice._portal_ensure_token()

        self.authenticate(self.user_portal.login, self.user_portal.login)
        for file in ['tesT.pdf', 'test.pdf']:
            self.url_open(
                url='/my/invoices/upload_withholding_certificate',
                data={
                    'name': file,
                    'thread_id': invoice.id,
                    'thread_model': 'account.move',
                    'access_token': invoice_access_token,
                    'csrf_token': http.Request.csrf_token(self)
                },
                files=[('file', (file, self.pdf_file, 'application/pdf'))],
            )

        self.authenticate(self.env.user.login, self.env.user.login)
        action = invoice.action_download_withholding_certificates()
        result = self.url_open(url=action['url'])
        self.assertRegex(result.headers.get('Content-Disposition', ''), rf"{invoice.name.replace('/', '_')}\.zip")
        # Ensure that the zip contains two files.
        with zipfile.ZipFile(io.BytesIO(result.content)) as downloaded_zip:
            file_count = len(downloaded_zip.filelist)
        self.assertEqual(file_count, 2)
