from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBERetrievePartner(TestUblImportBis3InvoiceBE):

    @freeze_time('2020-01-01')
    def test_import_partner_creation(self):
        self.partner_be.unlink()
        self.assertFalse(self.env['res.partner'].search([('vat', '=', 'BE0477472701')]))

        # Test the partner has been created.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner_creation',
            journal=self.company_data['default_journal_sale'],
        )
        partner = invoice.partner_id
        self.assertRecordValues(partner, [{
            'name': "My Belgian Partner",
            'street': "Rue des Trucs 9",
            'city': "Bidule",
            'zip': "6713",
            'vat': 'BE0477472701',
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
        }])

        # Test the partner has been retrieved.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner_creation',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.partner_id, [{'id': partner.id}])
