from odoo import fields
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblExportBis3DebitNoteBE(TestUblBis3Common, TestUblCiiBECommon):

    @classmethod
    def subfolders(cls):
        subfolder_format, _subfolder_document, subfolder_country = super().subfolders()
        return subfolder_format, 'debit_note', subfolder_country

    def test_debit_note_as_invoice_document(self):
        """ BIS3 export of Debit Note of a regular Customer Invoice because
        BIS3 does not have any specifications from Debit Notes.
        """
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=10.0, taxes_id=tax_21)

        invoice = self._create_invoice_one_line(
            invoice_date=fields.Date.from_string('2019-02-01'),
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )
        debit_note_args = {
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason',
            'copy_lines': True,
        }
        debit_note = self._create_debit_note(invoice, post=True, **debit_note_args)

        self._generate_invoice_ubl_file(debit_note)
        self._assert_invoice_ubl_file(debit_note, 'test_export_debit_note')
