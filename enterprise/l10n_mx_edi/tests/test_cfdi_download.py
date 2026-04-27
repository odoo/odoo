from freezegun import freeze_time
from io import BytesIO
from zipfile import ZipFile

from odoo.tests.common import HttpCase, tagged
from .common import TestMxEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIDownload(TestMxEdiCommon, HttpCase):

    @freeze_time('2017-01-01')
    def test_cfdi_download(self):
        invoice_1 = self._create_invoice()
        invoice_2 = self._create_invoice()
        invoice_3 = self._create_invoice()
        invoices = invoice_1 + invoice_2 + invoice_3
        with self.with_mocked_pac_sign_success():
            invoice_2._l10n_mx_edi_cfdi_invoice_try_send()
            invoice_3._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertTrue(invoice_2.l10n_mx_edi_cfdi_attachment_id)
        self.assertTrue(invoice_3.l10n_mx_edi_cfdi_attachment_id)
        action_download = invoices.action_invoice_download_cfdi()
        self.assertEqual(
            action_download['url'],
            f'/account/download_invoice_documents/{invoice_2.id},{invoice_3.id}/cfdi',
            'Only invoices with a CFDI should be called in the URL',
        )
        res_1 = self.url_open(action_download['url'])
        self.assertEqual(res_1.status_code, 200)
        self.assertIn(
            'oe_login_form',
            res_1.content.decode('utf-8'),
            'When not authenticated, the download is not possible.'
        )
        self.authenticate(self.env.user.login, self.env.user.login)
        res_2 = self.url_open(action_download['url'])
        self.assertEqual(res_2.status_code, 200)
        with ZipFile(BytesIO(res_2.content)) as zip_file:
            self.assertEqual(len(zip_file.filelist), 2)
            self.assertTrue(zip_file.NameToInfo.get(invoice_2.l10n_mx_edi_cfdi_attachment_id.name))
            self.assertTrue(zip_file.NameToInfo.get(invoice_3.l10n_mx_edi_cfdi_attachment_id.name))
