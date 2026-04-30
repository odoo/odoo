from datetime import date

from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

# The AE business terms of an imported XML, unless its test says otherwise. 380/381 decode as
# 'tax' for a company, only 'commercial' has its own code. '___ignore___' is the UUID in the expected XMLs.
AE_TERM_DEFAULTS = {
    'l10n_ae_invoice_type': 'tax',
    'l10n_ae_credit_note_reason': False,
    'l10n_ae_beneficiary_id': False,
    'l10n_ae_principal_id': False,
    'l10n_ae_uuid': '___ignore___',
}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestImportPintAe(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ae')
    def setUpClass(cls):
        super().setUpClass()

        # account_accountant disables the product retrieval by name unless enabled.
        if 'predict_bill_product' in cls.company_data['company']._fields:
            cls.company_data['company'].predict_bill_product = True

        # The identities the XMLs were exported with, for the partner retrieval to match.
        cls.company_data['company'].partner_id.write({
            'peppol_endpoint': '9900000097',
            'peppol_eas': '0235',
            'street': 'Al Maktoum Road',
            'city': 'Dubai',
            'zip': '00000',
            'state_id': cls.env.ref('base.state_ae_du').id,
            'vat': '100099099000003',
            'l10n_ae_registration_identifier': '112345678900001',
            'l10n_ae_registration_identifier_type': 'TL',
            'l10n_ae_authority_name': 'Trade License issuing Authority',
        })

        cls.partner_ae = cls.env['res.partner'].create({
            'name': 'AE Partner',
            # A company in every version: from saas-19.1, one with a VAT number is by default.
            'is_company': True,
            'country_id': cls.env.ref('base.ae').id,
            'street': 'Sheikh Zayed Road',
            'city': 'Dubai',
            'zip': '11111',
            'state_id': cls.env.ref('base.state_ae_du').id,
            'email': 'partner@ae-example.com',
            'invoice_edi_format': 'pint_ae',
            'bank_ids': [Command.create({'acc_number': 'AE070331234567890123456', 'allow_out_payment': True})],
            'vat': '100501099000003',
            'l10n_ae_registration_identifier': '112345678900003',
            'l10n_ae_registration_identifier_type': 'TL',
            'l10n_ae_authority_name': 'Trade License issuing Authority',
        })

        # The product of service_line.xml, matched on cbc:Name.
        cls.product_service = cls.env['product.product'].create({
            'name': 'product_service',
            'type': 'service',
            'lst_price': 100.0,
            'l10n_ae_hs_code': '998596',
        })

        # exports.xml is issued in USD; without a rate the currency cannot be converted on import.
        cls.env['res.currency.rate'].create({
            'name': '2025-01-01',
            'rate': 1 / 3.6725,
            'currency_id': cls.env.ref('base.USD').id,
            'company_id': cls.company_data['company'].id,
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @classmethod
    def _get_xml_content(cls, file_name):
        with file_open(f'l10n_ae_ubl_pint/tests/test_files/export/pint_ae/invoice/ae/{file_name}.xml', 'rb') as xml_file:
            return xml_file.read()

    def _import_xml(self, file_name, journal_type, xml_content=None):
        """ Import the export tests' expected {file_name}.xml, or xml_content when given, into a new
        invoice, the way an incoming file is.
        """
        attachment = self.env['ir.attachment'].create({
            'mimetype': 'application/xml',
            'name': f'{file_name}.xml',
            'raw': xml_content if xml_content is not None else self._get_xml_content(file_name),
        })
        journal = self.company_data[f'default_journal_{journal_type}']
        return journal._create_document_from_attachment(attachment.id)

    def _assert_import(self, file_name, journal_type, product, price_unit, expected_values, transaction_type_code=False):
        """ Import {file_name}.xml and check the invoice it gives: from 'AE Partner', dated 2025-03-05, in AED
        with the AE_TERM_DEFAULTS unless expected_values says otherwise, and a single line of product.

        The line label is 'name\nname': the exporter writes the product name as both cbc:Name and
        cbc:Description, which the base decoder joins.
        """
        invoice = self._import_xml(file_name, journal_type)
        self.assertRecordValues(invoice, [{
            'partner_id': self.partner_ae.id,
            'invoice_date': date(2025, 3, 5),
            'currency_id': self.env.ref('base.AED').id,
            **AE_TERM_DEFAULTS,
            **expected_values,
        }])
        # The transaction types are compared as their BTAE-02 flag string.
        self.assertEqual(invoice.l10n_ae_transaction_type_ids._get_flags_code(), transaction_type_code)
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': f'{product.name}\n{product.name}',
            'product_id': product.id,
            'quantity': 1.0,
            'price_unit': price_unit,
            'discount': 0.0,
        }])

    # -------------------------------------------------------------------------
    # DECODING: the export tests' files
    # -------------------------------------------------------------------------

    def test_import_commercial_credit_note(self):
        self._assert_import('commercial_credit_note', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_refund',
            'amount_untaxed': 1000.0,
            'amount_tax': 0.0,
            'amount_total': 1000.0,
            'l10n_ae_invoice_type': 'commercial',
            'l10n_ae_credit_note_reason': 'DL8.61.1.A',
        })

    def test_import_commercial_invoice(self):
        """ Category 'O' (out of scope): a 480 commercial invoice, no VAT at all. """
        self._assert_import('commercial_invoice', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 0.0,
            'amount_total': 1000.0,
            'l10n_ae_invoice_type': 'commercial',
        })

    def test_import_continuous_supply(self):
        self._assert_import('continuous_supply', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 0.0,
            'amount_total': 1000.0,
        }, transaction_type_code='00001000')

    def test_import_credit_note_billing_reference(self):
        self._assert_import('credit_note_billing_reference', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_refund',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
            'l10n_ae_credit_note_reason': 'DL8.61.1.A',
        })

    def test_import_credit_note(self):
        """ A CreditNote document: the root tag alone flips the move type, no negative amounts involved. """
        self._assert_import('credit_note', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_refund',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
            'l10n_ae_credit_note_reason': 'VD',
        })

    def test_import_disclosed_agent_billing_credit_note(self):
        self._assert_import('disclosed_agent_billing_credit_note', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_refund',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
            'l10n_ae_principal_id': '155667745601003',
            'l10n_ae_credit_note_reason': 'DL8.61.1.E',
        }, transaction_type_code='00000100')

    def test_import_disclosed_agent_billing(self):
        """ BTAE-14: the principal sits in its own cac:SellerSupplierParty block. """
        self._assert_import('disclosed_agent_billing', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
            'l10n_ae_principal_id': '155667745601003',
        }, transaction_type_code='00000100')

    def test_import_e_commerce(self):
        self._assert_import('e_commerce', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
        }, transaction_type_code='00000010')

    def test_import_exports(self):
        """ The only XML not in company currency: cbc:DocumentCurrencyCode is USD. """
        self._assert_import('exports', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'currency_id': self.env.ref('base.USD').id,
            'amount_untaxed': 1000.0,
            'amount_tax': 0.0,
            'amount_total': 1000.0,
        }, transaction_type_code='00000001')

    def test_import_free_trade_zone(self):
        """ BTAE-01: the beneficiary sits in its own cac:BuyerCustomerParty block. """
        self._assert_import('free_trade_zone', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
            'l10n_ae_beneficiary_id': '189098765401003',
        }, transaction_type_code='10000000')

    def test_import_self_billing_credit_note(self):
        """ Self-billing: 'AE Partner' is the supplier, so it decodes into a vendor refund. """
        self._assert_import('self_billing_credit_note', 'purchase', self.product_a, 800.0, {
            'move_type': 'in_refund',
            'amount_untaxed': 800.0,
            'amount_tax': 40.0,
            'amount_total': 840.0,
            'l10n_ae_credit_note_reason': 'VD',
        })

    def test_import_self_billing_invoice(self):
        """ Self-billing: 'AE Partner' is the supplier, so it decodes into a vendor bill. """
        self._assert_import('self_billing_invoice', 'purchase', self.product_a, 800.0, {
            'move_type': 'in_invoice',
            'amount_untaxed': 800.0,
            'amount_tax': 40.0,
            'amount_total': 840.0,
        })

    def test_import_service_line(self):
        self._assert_import('service_line', 'sale', self.product_service, 100.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 100.0,
            'amount_tax': 5.0,
            'amount_total': 105.0,
        })

    def test_import_standard_invoice_mandatory_fields(self):
        self._assert_import('standard_invoice_mandatory_fields', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
        })

    def test_import_standard_tax_invoice(self):
        self._assert_import('standard_tax_invoice', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
        })

    def test_import_summary_tax_invoice(self):
        self._assert_import('summary_tax_invoice', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 50.0,
            'amount_total': 1050.0,
        }, transaction_type_code='00010000')

    def test_import_zero_rated_supplies(self):
        """ Category 'Z' (zero rated): a real 0% tax, so no tax amount but still a tax. """
        self._assert_import('zero_rated_supplies', 'sale', self.product_a, 1000.0, {
            'move_type': 'out_invoice',
            'amount_untaxed': 1000.0,
            'amount_tax': 0.0,
            'amount_total': 1000.0,
        })

    # -------------------------------------------------------------------------
    # DECODING: accounting values
    # -------------------------------------------------------------------------

    def test_import_invoice_reference_fields(self):
        """ cbc:ID and cac:OrderReference feed the bill reference and the origin. """
        # Exported without a Customer Reference, so without cac:OrderReference.
        invoice = self._import_xml('self_billing_invoice', 'purchase')
        self.assertRecordValues(invoice, [{
            'ref': 'INV/2025/00001',
            'invoice_origin': False,
        }])

        # On the sale journal: purchase, when installed, clears the origin of a bill matching no purchase order.
        credit_note = self._import_xml('credit_note_billing_reference', 'sale')
        self.assertEqual(credit_note.invoice_origin, 'Reversal of: INV/2025/00002')

    def test_import_taxes_are_matched(self):
        """ The tax category and rate resolve to a real tax, not a balanced but untaxed invoice. """
        invoice = self._import_xml('standard_tax_invoice', 'sale')

        taxes = invoice.invoice_line_ids.tax_ids
        self.assertEqual(len(taxes), 1, "The 5% standard rated tax should have been matched.")
        self.assertEqual(taxes.amount, 5.0)
        self.assertEqual(invoice.amount_tax, 50.0)

    def test_import_zero_rated_keeps_a_tax(self):
        """ Category 'Z' is a real 0% tax, it must not decode as 'no tax at all'. """
        invoice = self._import_xml('zero_rated_supplies', 'sale')

        taxes = invoice.invoice_line_ids.tax_ids
        self.assertEqual(len(taxes), 1, "The zero rated tax should have been matched.")
        self.assertEqual(taxes.amount, 0.0)

    def test_import_attachment_is_kept_on_the_bill(self):
        """ The decoded XML must stay attached to a purchase document as its ubl_cii_xml_file. """
        invoice = self._import_xml('self_billing_invoice', 'purchase')

        self.assertTrue(invoice.ubl_cii_xml_id, "The source XML should be kept on the bill.")
        self.assertEqual(invoice.ubl_cii_xml_id.name, 'self_billing_invoice.xml')

    # -------------------------------------------------------------------------
    # DECODING: AE business terms (PINT AE semantic model)
    # -------------------------------------------------------------------------

    def test_import_keeps_the_document_uuid(self):
        """ BTAE-07: the issuer's UUID is kept, a document without one gets none until it is exported. """
        invoice = self._import_xml('standard_tax_invoice', 'sale')
        self.assertEqual(invoice.l10n_ae_uuid, '___ignore___')

        content = self._get_xml_content('standard_tax_invoice')
        tree = etree.fromstring(content)
        tree.remove(tree.find('{*}UUID'))

        invoice = self._import_xml('standard_tax_invoice', 'sale', xml_content=etree.tostring(tree))
        self.assertFalse(invoice.l10n_ae_uuid)

    def test_import_incoterm(self):
        """ BTAE-22 survives the round trip. The XMLs have none, so it's added here. """
        content = self._get_xml_content('standard_tax_invoice')
        tree = etree.fromstring(content)
        delivery = tree.find('{*}Delivery')
        self.assertIsNotNone(delivery, "The XML should carry a cac:Delivery to hang BTAE-22 on.")
        terms = etree.SubElement(delivery, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}DeliveryTerms')
        etree.SubElement(terms, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID').text = 'CIF'

        invoice = self._import_xml('standard_tax_invoice', 'sale', xml_content=etree.tostring(tree))

        self.assertEqual(invoice.invoice_incoterm_id, self.env.ref('account.incoterm_CIF'))
