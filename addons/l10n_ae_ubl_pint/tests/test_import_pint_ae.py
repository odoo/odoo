from datetime import date

from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

# What an AE document carries when none of the AE specific business terms apply. Every fixture is
# checked against these, overridden by its own 'ae' entry below, so a term leaking from one
# document type into another is caught rather than going unnoticed.
#
# l10n_ae_invoice_type defaults to 'simplified' because a 380/381 cannot say which of
# 'simplified' or 'tax' produced it - only 480/81 ('commercial') survives the round trip.
# l10n_ae_uuid is '___ignore___' because that is what test_export_pint_ae.py writes into the
# fixtures in place of the database specific UUID; a decoded document keeping it proves the
# sender's UUID won over the one create() generates.
AE_TERM_DEFAULTS = {
    'l10n_ae_invoice_type': 'simplified',
    'l10n_ae_invoice_transaction_type': False,
    'l10n_ae_credit_note_reason': False,
    'l10n_ae_beneficiary_id': False,
    'l10n_ae_principal_id': False,
    'l10n_ae_uuid': '___ignore___',
}

# What decoding each fixture under tests/expected_xml must produce.
#
# The fixtures are the exact files test_export_pint_ae.py asserts on, so this suite closes the
# round trip: whatever the exporter writes, the decoder must read back. 'journal' says which side
# of the document we are: the regular billing profile has us as the supplier and 'AE Partner' as
# the customer (a sale document), while the selfbilling profile has them reversed (a purchase
# document). Either way the counterparty is 'AE Partner', which is what 'partner' below asserts.
#
# Amounts mirror cac:LegalMonetaryTotal / cac:TaxTotal of each file; 'line' mirrors its single
# cac:InvoiceLine / cac:CreditNoteLine. 'item' is the value the exporter writes to BOTH
# cbc:Name and cbc:Description - see _assert_line below for what the decoder makes of that.
# 'ae' holds only the AE business terms that differ from AE_TERM_DEFAULTS.
EXPECTED_IMPORT_OUTPUT = {
    'standard_tax_invoice': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 50.0, 1050.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {},
    },
    'standard_invoice_mandatory_fields': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 50.0, 1050.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {},
    },
    'summary_tax_invoice': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 50.0, 1050.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {'l10n_ae_invoice_transaction_type': '00010000'},
    },
    'free_trade_zone': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 50.0, 1050.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        # BTAE-01: the beneficiary sits in its own cac:BuyerCustomerParty block.
        'ae': {
            'l10n_ae_invoice_transaction_type': '10000000',
            'l10n_ae_beneficiary_id': '189098765401003',
        },
    },
    'disclosed_agent_billing': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 50.0, 1050.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        # BTAE-14: the principal sits in its own cac:SellerSupplierParty block.
        'ae': {
            'l10n_ae_invoice_transaction_type': '00000100',
            'l10n_ae_principal_id': '155667745601003',
        },
    },
    'e_commerce': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 50.0, 1050.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {'l10n_ae_invoice_transaction_type': '00000010'},
    },
    # Category 'Z' (zero rated): a real 0% tax, so tax amount is 0 but a tax is still expected.
    'zero_rated_supplies': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 0.0, 1000.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {},
    },
    'continuous_supply': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 0.0, 1000.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {'l10n_ae_invoice_transaction_type': '00001000'},
    },
    # The only fixture not in company currency - cbc:DocumentCurrencyCode is USD.
    'exports': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'USD',
        'amounts': (1000.0, 0.0, 1000.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {'l10n_ae_invoice_transaction_type': '00000001'},
    },
    # Category 'O' (out of scope): 480 commercial invoice, no VAT at all.
    'commercial_invoice': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (1000.0, 0.0, 1000.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {'l10n_ae_invoice_type': 'commercial'},
    },
    'service_line': {
        'journal': 'sale', 'move_type': 'out_invoice', 'currency': 'AED',
        'amounts': (100.0, 5.0, 105.0),
        'line': {'item': 'product_service', 'quantity': 1.0, 'price_unit': 100.0, 'discount': 0.0},
        'ae': {},
    },
    # CreditNote documents: the root tag alone flips the move type, no negative amounts involved.
    'credit_note': {
        'journal': 'sale', 'move_type': 'out_refund', 'currency': 'AED',
        'amounts': (1000.0, 50.0, 1050.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {'l10n_ae_credit_note_reason': 'VD'},
    },
    # The one fixture with a line discount: PriceAmount 1000 against LineExtensionAmount 900.
    'credit_note_billing_reference': {
        'journal': 'sale', 'move_type': 'out_refund', 'currency': 'AED',
        'amounts': (900.0, 45.0, 945.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 10.0},
        'ae': {'l10n_ae_credit_note_reason': 'DL8.61.1.A'},
    },
    'commercial_credit_note': {
        'journal': 'sale', 'move_type': 'out_refund', 'currency': 'AED',
        'amounts': (1000.0, 0.0, 1000.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {
            'l10n_ae_invoice_type': 'commercial',
            'l10n_ae_credit_note_reason': 'DL8.61.1.A',
        },
    },
    'disclosed_agent_billing_credit_note': {
        'journal': 'sale', 'move_type': 'out_refund', 'currency': 'AED',
        'amounts': (1000.0, 50.0, 1050.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 1000.0, 'discount': 0.0},
        'ae': {
            'l10n_ae_invoice_transaction_type': '00000100',
            'l10n_ae_principal_id': '155667745601003',
            'l10n_ae_credit_note_reason': 'DL8.61.1.E',
        },
    },
    # Self-billing: 'AE Partner' is the supplier, so these decode into vendor documents.
    'self_billing_invoice': {
        'journal': 'purchase', 'move_type': 'in_invoice', 'currency': 'AED',
        'amounts': (800.0, 40.0, 840.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 800.0, 'discount': 0.0},
        'ae': {},
    },
    'self_billing_credit_note': {
        'journal': 'purchase', 'move_type': 'in_refund', 'currency': 'AED',
        'amounts': (800.0, 40.0, 840.0),
        'line': {'item': 'product_a', 'quantity': 1.0, 'price_unit': 800.0, 'discount': 0.0},
        'ae': {'l10n_ae_credit_note_reason': 'VD'},
    },
}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestImportPintAe(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ae')
    def setUpClass(cls):
        super().setUpClass()

        # Same company/partner identities the fixtures were exported with, so that the partner
        # retrieval actually has something to match on (VAT first, then EAS/endpoint).
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

        # service_line.xml was exported from a service product, and product retrieval matches on
        # cbc:Name - without it that fixture decodes to a line with no product at all.
        cls.product_service = cls.env['product.product'].create({
            'name': 'product_service',
            'type': 'service',
            'lst_price': 100.0,
            'l10n_ae_classification_code': '998596',
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
    def _get_fixture_content(cls, fixture_name):
        with file_open(f'l10n_ae_ubl_pint/tests/expected_xml/{fixture_name}.xml', 'rb') as fixture_file:
            return fixture_file.read()

    @classmethod
    def _get_fixture_attachment(cls, fixture_name, file_content=None):
        """ Build an ir.attachment out of one of the export fixtures. """
        return cls.env['ir.attachment'].create({
            'mimetype': 'application/xml',
            'name': f'{fixture_name}.xml',
            'raw': file_content if file_content is not None else cls._get_fixture_content(fixture_name),
        })

    def _import_fixture(self, fixture_name, journal_type, file_content=None):
        """ Decode one fixture into a brand new invoice, the way an incoming file is handled. """
        attachment = self._get_fixture_attachment(fixture_name, file_content=file_content)
        journal = self.company_data[f'default_journal_{journal_type}']
        return journal._create_document_from_attachment(attachment.id)

    def _assert_line(self, invoice, expected_line):
        """ Assert the single decoded line of an invoice.

        The label is checked as 'item\\nitem': the base UBL decoder joins cbc:Name and
        cbc:Description with a newline whenever both are present
        (account.edi.ubl's _import_ubl_invoice_line_add_name), and the AE exporter writes the
        product name into both. So the duplication below is the exporter and the base decoder
        agreeing, not a decode error - assert it explicitly so a change in either side is caught.

        product_id is asserted too: an unmatched product still yields the right label and amounts,
        so without it a silent retrieval failure would go unnoticed.
        """
        item = expected_line['item']
        product = {
            'product_a': self.product_a,
            'product_service': self.product_service,
        }[item]

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': f'{item}\n{item}',
            'product_id': product.id,
            'quantity': expected_line['quantity'],
            'price_unit': expected_line['price_unit'],
            'discount': expected_line['discount'],
        }])

    # -------------------------------------------------------------------------
    # ROUTING
    # -------------------------------------------------------------------------

    def test_import_file_type_is_pint_ae(self):
        """ Every AE fixture must be routed to the AE format, not to the generic UBL one.

        Both AE profiles are covered: the billing fixtures carry
        'urn:peppol:pint:billing-1@ae-1' and the self-billing ones
        'urn:peppol:pint:selfbilling-1@ae-1'. Without the selfbilling id in the routing, the
        latter fall through to the generic cbc:UBLVersionID check and decode as plain UBL 2.1.
        """
        for fixture_name in EXPECTED_IMPORT_OUTPUT:
            with self.subTest(fixture=fixture_name):
                attachment = self._get_fixture_attachment(fixture_name)
                file_data = self.env['account.move']._to_files_data(attachment)[0]

                self.assertEqual(
                    self.env['account.move']._get_import_file_type(file_data),
                    'account.edi.xml.pint_ae',
                )

    def test_import_decoder_is_registered(self):
        """ Routing is not enough: the format must also be accepted as a decoder.

        account.edi.xml.pint_ae is built on account.edi.ubl_pint rather than on
        account.edi.xml.ubl_20, so it is only reachable once account.edi.ubl_pint's children are
        part of the importable models in account_edi_ubl_cii's _get_edi_decoder.
        """
        attachment = self._get_fixture_attachment('standard_tax_invoice')
        file_data = self.env['account.move']._to_files_data(attachment)[0]

        decoder_info = self.env['account.move']._get_edi_decoder(file_data, new=True)
        self.assertIsNotNone(decoder_info, "No decoder was found for a PINT AE file.")
        self.assertEqual(
            decoder_info['decoder'].__self__._name,
            'account.edi.xml.pint_ae',
        )

    # -------------------------------------------------------------------------
    # DECODING: accounting values
    # -------------------------------------------------------------------------

    def test_import_accounting_values(self):
        """ Decode every exported fixture and check the invoice it produces. """
        for fixture_name, expected in EXPECTED_IMPORT_OUTPUT.items():
            with self.subTest(fixture=fixture_name):
                invoice = self._import_fixture(fixture_name, expected['journal'])

                amount_untaxed, amount_tax, amount_total = expected['amounts']
                self.assertRecordValues(invoice, [{
                    'move_type': expected['move_type'],
                    'partner_id': self.partner_ae.id,
                    'invoice_date': date(2025, 3, 5),
                    'currency_id': self.env.ref(f"base.{expected['currency']}").id,
                    'amount_untaxed': amount_untaxed,
                    'amount_tax': amount_tax,
                    'amount_total': amount_total,
                }])

                self._assert_line(invoice, expected['line'])

    def test_import_invoice_reference_fields(self):
        """ cbc:ID and cac:OrderReference feed the bill reference and the origin. """
        invoice = self._import_fixture('self_billing_invoice', 'purchase')

        self.assertRecordValues(invoice, [{
            'ref': 'INV/2025/00001',
            'invoice_origin': 'INV/2025/00001',
        }])

    def test_import_line_discount_from_net_amount(self):
        """ A line whose net amount is below price x quantity must come back as a discount.

        credit_note_billing_reference is the only fixture exported with one: cbc:PriceAmount is
        1000 while cbc:LineExtensionAmount is 900, which is a 10% discount.
        """
        invoice = self._import_fixture('credit_note_billing_reference', 'sale')

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 1000.0,
            'discount': 10.0,
            'price_subtotal': 900.0,
        }])

    def test_import_taxes_are_matched(self):
        """ The tax category and rate in the file must resolve to a real Odoo tax.

        Guards against a decode that silently drops the tax and still balances, which would leave
        the amounts right but the invoice untaxable.
        """
        invoice = self._import_fixture('standard_tax_invoice', 'sale')

        taxes = invoice.invoice_line_ids.tax_ids
        self.assertEqual(len(taxes), 1, "The 5% standard rated tax should have been matched.")
        self.assertEqual(taxes.amount, 5.0)
        self.assertEqual(invoice.amount_tax, 50.0)

    def test_import_zero_rated_keeps_a_tax(self):
        """ Category 'Z' is a real 0% tax, it must not decode as 'no tax at all'. """
        invoice = self._import_fixture('zero_rated_supplies', 'sale')

        taxes = invoice.invoice_line_ids.tax_ids
        self.assertEqual(len(taxes), 1, "The zero rated tax should have been matched.")
        self.assertEqual(taxes.amount, 0.0)

    def test_import_attachment_is_kept_on_the_bill(self):
        """ The decoded XML must stay attached to a purchase document as its ubl_cii_xml_file. """
        invoice = self._import_fixture('self_billing_invoice', 'purchase')

        self.assertTrue(invoice.ubl_cii_xml_id, "The source XML should be kept on the bill.")
        self.assertEqual(invoice.ubl_cii_xml_id.name, 'self_billing_invoice.xml')

    # -------------------------------------------------------------------------
    # DECODING: AE business terms (PINT AE semantic model)
    # -------------------------------------------------------------------------

    def test_import_ae_business_terms(self):
        """ The AE specific business terms must survive the round trip, not just the amounts.

        A generic UBL decode reads none of these: it would produce an invoice with correct
        totals whose transaction type, credit note reason, beneficiary, principal and document
        UUID are all silently lost.
        """
        for fixture_name, expected in EXPECTED_IMPORT_OUTPUT.items():
            with self.subTest(fixture=fixture_name):
                invoice = self._import_fixture(fixture_name, expected['journal'])

                self.assertRecordValues(invoice, [{**AE_TERM_DEFAULTS, **expected['ae']}])

    def test_import_keeps_the_document_uuid(self):
        """ BTAE-02: the issuer's UUID wins over the one create() derives from this database. """
        invoice = self._import_fixture('standard_tax_invoice', 'sale')
        self.assertEqual(invoice.l10n_ae_uuid, '___ignore___')

        # And a document without a UUID still gets a locally generated one.
        content = self._get_fixture_content('standard_tax_invoice')
        tree = etree.fromstring(content)
        tree.remove(tree.find('{*}UUID'))

        invoice = self._import_fixture('standard_tax_invoice', 'sale', file_content=etree.tostring(tree))
        self.assertTrue(invoice.l10n_ae_uuid)
        self.assertNotEqual(invoice.l10n_ae_uuid, '___ignore___')

    def test_import_card_payment_means(self):
        """ UNCL4461 code 55: cac:CardAccount carries the masked card number and its network.

        No exported fixture uses a card, so the payment means block is swapped for one here.
        """
        content = self._get_fixture_content('standard_tax_invoice')
        tree = etree.fromstring(content)
        cbc = '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}'
        cac = '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}'

        payment_means = tree.find(f'{cac}PaymentMeans')
        payment_means.find(f'{cbc}PaymentMeansCode').text = '55'
        card_account = etree.SubElement(payment_means, f'{cac}CardAccount')
        etree.SubElement(card_account, f'{cbc}PrimaryAccountNumberID').text = '************1234'
        etree.SubElement(card_account, f'{cbc}NetworkID').text = 'VISA'

        invoice = self._import_fixture('standard_tax_invoice', 'sale', file_content=etree.tostring(tree))

        self.assertRecordValues(invoice, [{
            'l10n_ae_card_number': '************1234',
            'l10n_ae_card_network': 'VISA',
        }])

    def test_import_unknown_ae_codes_are_ignored(self):
        """ A code this module does not model must be skipped, not abort the whole import.

        Incoming documents are written by other systems; writing an unknown code straight onto a
        Selection field would raise and lose the document entirely.
        """
        content = self._get_fixture_content('credit_note')
        tree = etree.fromstring(content)
        tree.find('{*}ProfileExecutionID').text = '11111111'
        tree.find('{*}DiscrepancyResponse/{*}ResponseCode').text = 'NOT-A-REASON'

        invoice = self._import_fixture('credit_note', 'sale', file_content=etree.tostring(tree))

        # The document still decodes, with the unsupported terms left unset.
        self.assertRecordValues(invoice, [{
            'move_type': 'out_refund',
            'amount_total': 1050.0,
            'l10n_ae_invoice_transaction_type': False,
            'l10n_ae_credit_note_reason': False,
        }])
