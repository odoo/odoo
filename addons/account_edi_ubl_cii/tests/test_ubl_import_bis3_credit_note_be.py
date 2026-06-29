from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3CreditNoteBE(TestUblBis3Common, TestUblCiiBECommon):

    @classmethod
    def subfolders(cls):
        subfolder_format, _subfolder_document, subfolder_country = super().subfolders()
        return subfolder_format, 'credit_note', subfolder_country

    def test_import_credit_note_from_negative_invoice(self):
        self.percent_tax(21.0, type_tax_use='purchase')
        invoice = self._import_invoice_as_attachment_on(test_name='test_import_credit_note_from_invoice_with_negative_lines')
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.amount_total, 121.0)
