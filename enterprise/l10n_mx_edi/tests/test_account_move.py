from freezegun import freeze_time
from .common import TestMxEdiCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIAccountMove(TestMxEdiCommon):

    @freeze_time('2017-01-01')
    def test_extra_print_items(self):
        invoice = self._create_invoice()
        print_items_before = invoice.get_extra_print_items()
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        print_items_after = invoice.get_extra_print_items()
        self.assertEqual(len(print_items_before) + 1, len(print_items_after))

    @freeze_time('2017-01-01')
    def test_get_invoice_legal_documents_cfdi(self):
        invoice_with_cfdi = self._create_invoice()
        invoice_without_cfdi = self._create_invoice()
        with self.with_mocked_pac_sign_success():
            invoice_with_cfdi._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertEqual(invoice_with_cfdi._get_invoice_legal_documents('cfdi'), {
            'filename': invoice_with_cfdi.l10n_mx_edi_cfdi_attachment_id.name,
            'filetype': 'xml',
            'content': invoice_with_cfdi.l10n_mx_edi_cfdi_attachment_id.raw,
        })
        self.assertFalse(invoice_without_cfdi._get_invoice_legal_documents('cfdi'))
