from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLAttachedDocument(TestUBLCommon):

    @classmethod
    @TestUBLCommon.setup_country('au')
    def setUpClass(cls):
        """ AttachedDocuments are a wrapper of multiple different types of documents, as such we
        need a country/localization to import a file properly. This is not Australia specific
        but instead just re-using the files and setup from other test classes. """
        super().setUpClass()

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Spring St.",
            'zip': "3002",
            'city': "Melbourne",
            'vat': '83 914 571 673',
            'phone': '+31 180 6 225789',
            'email': 'info@outlook.au',
            'country_id': cls.env.ref('base.au').id,
            'bank_ids': [(0, 0, {'acc_number': '000099998B57'})],
            'ref': 'ref_partner_1',
            'invoice_edi_format': 'ubl_a_nz',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Parliament Dr",
            'zip': "2600",
            'city': "Canberra",
            'vat': '53 930 548 027',
            'country_id': cls.env.ref('base.au').id,
            'bank_ids': [(0, 0, {'acc_number': '93999574162167'})],
            'ref': 'ref_partner_2',
            'invoice_edi_format': 'ubl_a_nz',
        })

        cls.tax_10 = cls.env['account.tax'].create({
            'name': 'tax_10',
            'amount_type': 'percent',
            'amount': 10,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.au').id,
        })

    def test_import_attached_document_invoice_xml(self):
        """ The original invoice can be stored in one of two places, either as a base64 encoded
        string in EmbeddedDocumentBinaryObject or as a CDATA[] value inside of an
        ExternalReference/Description tag. Importing such files should ignore the outside wrapper
        and return the correct original invoice takes from a_nz_out_invoice. """
        self._assert_imported_invoice_from_file(
            subfolder='tests/test_files/from_odoo',
            filename='a_nz_out_invoice_attacheddocument_b64.xml',
            invoice_vals={
                'currency_id': self.other_currency.id,
                'amount_total': 2950.2,
                'amount_tax': 268.2,
                'invoice_lines': [{'price_subtotal': x} for x in (1782, 1000, -100)]
            },
        )

        self._assert_imported_invoice_from_file(
            subfolder='tests/test_files/from_odoo',
            filename='a_nz_out_invoice_attacheddocument_description.xml',
            invoice_vals={
                'currency_id': self.other_currency.id,
                'amount_total': 2950.2,
                'amount_tax': 268.2,
                'invoice_lines': [{'price_subtotal': x} for x in (1782, 1000, -100)]
            },
        )
