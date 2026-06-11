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

    @freeze_time('2020-01-01')
    def test_import_partner_creation_email(self):
        self.partner_be.unlink()
        self.assertFalse(self.env['res.partner'].search([('vat', '=', 'DE0477472701')]))

        # Test the partner has been created.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner_creation_email',
            journal=self.company_data['default_journal_sale'],
        )
        partner = invoice.partner_id
        self.assertRecordValues(partner, [{
            'name': "My Belgian Partner",
            'street': "Rue des Trucs 9",
            'city': "Bidule",
            'zip': "6713",
            'vat': 'BE0477472701',
            'peppol_eas': 'EM',
            'peppol_endpoint': 'info@belgium.test',
        }])

        # Test the partner has been retrieved.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner_creation_email',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.partner_id, [{'id': partner.id}])

    @freeze_time('2020-01-01')
    def test_import_partner_retrieval_no_contact(self):
        self.env['res.partner'].create({
            'parent_id': self.partner_be.id,
            'name': 'My contact',
            'company_id': self.partner_be.company_id.id,
        })

        # Test the partner has been retrieved.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_partner_creation',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertEqual(self.partner_be, invoice.partner_id, "We find the belgian partner, not his contact")

    def test_import_bill_vat_in_party_identification(self):
        """ Some Peppol emitters add the supplier VAT only in
        cac:PartyIdentification/cbc:ID, not in PartyTaxScheme/cbc:CompanyID.
        """
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_bill_vat_in_party_identification',
            journal=self.company_data['default_journal_purchase'],
        )
        self.assertEqual(invoice.partner_id.vat, 'BE0239843188')
        self.assertEqual(invoice.partner_bank_id.partner_id, invoice.partner_id)

    def test_partial_import_partner_retrieval_bank_account_number(self):
        """Check that the bank account number is used to retrieve the partner when importing a Bis 3 xml."""
        partner_bank = self.env['res.partner.bank'].create({
            'acc_number': 'BE43200112345678',
            'partner_id': self.partner_a.id,
            'allow_out_payment': True,
        })
        # Update partner_a and link it with the bank account we created
        self.partner_a.update({
            'name': "Test Partner",
            'street': "42 Maze street",
            'city': "Berlin",
            'zip': "6534",
            'vat': False,  # Clear the VAT field so the partner can only be found through the bank account number
            'country_id': self.env.ref('base.be').id,
            'bank_ids': partner_bank.ids,
        })
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_partner_retrieval_bank_account_number',
            journal=self.company_data['default_journal_sale'],
        )
        # partner_a should be matched through the bank account number and its VAT should be filled in from the XML
        self.assertEqual(invoice.partner_id, self.partner_a)
        self.assertEqual(invoice.partner_id.vat, self.partner_a.vat)

        # Change the VAT to trigger the VAT mismatch logic
        self.partner_a.vat = 'BE4695478703'
        # A new partner should be created
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_partner_retrieval_bank_account_number',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.partner_id, [{
            'name': "My Belgian Partner",
            'street': "Rue des Trucs 9",
            'city': "Bidule",
            'zip': "6713",
            'vat': 'BE4018517582',
            'country_id': self.env.ref('base.be').id,
        }])
