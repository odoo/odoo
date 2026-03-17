from odoo.addons.account_edi_ubl_cii.tests.test_cii_import_facturx_fr import CiiImportFacturXFR
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCiiImportFacturXFRRetrievePartner(CiiImportFacturXFR):

    @freeze_time('2020-01-01')
    def test_import_partner_creation(self):
        self.partner_fr.unlink()
        self.assertFalse(self.env['res.partner'].search([('vat', '=', 'FR05677404089')]))

        # Test the partner has been created.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner_creation',
            journal=self.company_data['default_journal_sale'],
        )
        partner = invoice.partner_id
        self.assertRecordValues(partner, [{
            'name': 'partner_fr',
            'street': "Rue Jean Jaurès, 42",
            'zip': "75000",
            'city': "Paris",
            'vat': 'FR05677404089',
        }])

        # Test the partner has been retrieved.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner_creation',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.partner_id, [{'id': partner.id}])

    @freeze_time('2020-01-01')
    def test_import_partner_retrieval_no_contact(self):
        self.env['res.partner'].create({
            'parent_id': self.partner_fr.id,
            'name': 'My contact',
            'company_id': self.partner_fr.company_id.id,
        })

        # Test the partner has been retrieved.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner_creation',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertEqual(self.partner_fr, invoice.partner_id, "We find the belgian partner, not his contact")
