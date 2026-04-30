from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestExportPintAe(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ae')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].partner_id.write({
            'peppol_endpoint': '9900000097',
            'peppol_eas': '0235',
            'street': 'Al Maktoum Road',
            'city': 'Dubai',
            'zip': '00000',
            'state_id': cls.env.ref('base.state_ae_du').id,
            # A real vat (matching the TRN format: 15 digits, starts '1', ends '03') makes
            # _ubl_add_party_tax_scheme_nodes_vat_gst build a proper TaxScheme/ID='VAT' node -
            # without it, account.edi.ubl_pint falls back to a peppol_endpoint-based pseudo tax
            # scheme (TaxScheme/ID=peppol_eas, CompanyID=peppol_endpoint) that AE's own
            # ibr-133/148-ae reject (wrong scheme id, endpoint isn't a valid 10-digit TIN).
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

        # Standard AE CoA taxes (l10n_ae/data/template/account.tax-ae.csv) already carry the
        # right ubl_cii_tax_category_code - reuse them instead of fabricating ad-hoc ones.
        cls.tax_zero_rated = cls.env['account.chart.template'].ref('uae_sale_tax_0')
        cls.tax_out_of_scope = cls.env['account.chart.template'].ref('uae_out_of_scope')

        # ibr-184-ae: Item classification identifier is mandatory for Goods lines - product_a
        # (the shared line item every test here uses) has no HS code by default.
        cls.product_a.l10n_ae_classification_code = '7214'

        # ibr-185-ae: Service accounting code (BTAE-17) is mandatory for Services lines - a
        # dedicated service product, since product_a is Goods-typed.
        cls.product_service = cls.env['product.product'].create({
            'name': 'product_service',
            'type': 'service',
            'lst_price': 100.0,
            'l10n_ae_classification_code': '998596',
        })

    def _generate_invoice_xml(self, move_type='out_invoice', tax=None, product=None, **kwargs):
        invoice = self._create_invoice(
            move_type=move_type,
            partner_id=self.partner_ae,
            invoice_line_ids=[self._prepare_invoice_line(product_id=product or self.product_a, tax_ids=tax or self.tax_sale_a)],
            name='INV/2025/00001',
            post=True,
            **kwargs,
        )
        xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
        self.assertFalse(errors)
        xml_tree = self.get_xml_tree_from_string(xml_content)
        # l10n_ae_uuid is derived from database.uuid (randomly assigned per database) + move id -
        # it can never be reproduced across two different databases, so it can't be part of a
        # fixture comparison (same workaround test_export_credit_note_with_billing_reference
        # already applies inline for its own hand-rolled generation).
        uuid_node = xml_tree.find('.//{*}UUID')
        if uuid_node is not None:
            uuid_node.text = '___ignore___'
        return xml_tree

    def _assert_matches_fixture(self, xml_tree, fixture_name):
        fixture_path = f'l10n_ae_ubl_pint/tests/expected_xml/{fixture_name}.xml'
        with file_open(fixture_path, 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(xml_tree, self.get_xml_tree_from_string(expected_xml))

    def test_export_invoice(self):
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml()

        self._assert_matches_fixture(xml_tree, 'standard_tax_invoice')

    def test_export_credit_note_with_reason(self):
        # ibr-055-ae: a preceding invoice reference is mandatory for every credit note reason
        # except 'VD' (Volume Discount) - this test exercises the one reason that's valid
        # standalone; test_export_credit_note_with_billing_reference covers the opposite case
        # (a real reason, with the required reference to the invoice it reverses).
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(
                move_type='out_refund',
                l10n_ae_credit_note_reason='VD',
            )

        self._assert_matches_fixture(xml_tree, 'credit_note')

    def test_export_credit_note_with_billing_reference(self):
        # Credit note as an actual reversal of a posted invoice, matching official_credit_note.xml:
        # BTAE-03 reason + BillingReference back to the original invoice + a line discount.
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a, discount=10)],
                name='INV/2025/00002',
                post=True,
            )
            credit_note = self._reverse_invoice(invoice, post=True, l10n_ae_credit_note_reason='DL8.61.1.A')

            xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(credit_note)
            self.assertFalse(errors)
            xml_tree = self.get_xml_tree_from_string(xml_content)
            uuid_node = xml_tree.find('.//{*}UUID')
            if uuid_node is not None:
                uuid_node.text = '___ignore___'

        self._assert_matches_fixture(xml_tree, 'credit_note_billing_reference')

    def test_export_commercial_invoice(self):
        # aligned-ibrp-o-09: VAT amount MUST be 0 for category 'O' - a Commercial invoice is a
        # non-fiscal document, so it must actually carry no real tax (tax_out_of_scope, 0%), not
        # just get relabeled 'O' on top of a real rate.
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(l10n_ae_invoice_type='commercial', tax=self.tax_out_of_scope)

        self._assert_matches_fixture(xml_tree, 'commercial_invoice')

    def test_export_commercial_credit_note(self):
        # Same as test_export_commercial_invoice but reversed: category 'O', with a
        # BillingReference back to the original commercial invoice. ibr-055-ae requires the
        # opposite pairing of test_export_credit_note_with_reason's 'VD': a BillingReference
        # needs a real reason code, 'VD' must have no BillingReference at all.
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_out_of_scope)],
                name='INV/2025/00002',
                l10n_ae_invoice_type='commercial',
                post=True,
            )
            credit_note = self._reverse_invoice(invoice, post=True, l10n_ae_credit_note_reason='DL8.61.1.A')

            xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(credit_note)
            self.assertFalse(errors)
            xml_tree = self.get_xml_tree_from_string(xml_content)
            uuid_node = xml_tree.find('.//{*}UUID')
            if uuid_node is not None:
                uuid_node.text = '___ignore___'

        self._assert_matches_fixture(xml_tree, 'commercial_credit_note')

    def test_export_exports(self):
        # 1 USD = 3.6725 AED. Scoped to this test only (not setUpClass): a foreign-currency
        # rate anywhere in the company throws off tax-amount rounding for every other,
        # AED-only test too (some base multi-currency rounding path picks up any rate present).
        self.env['res.currency.rate'].create({
            'name': '2025-01-01',
            'rate': 1 / 3.6725,
            'currency_id': self.env.ref('base.USD').id,
            'company_id': self.company_data['company'].id,
        })

        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(
                l10n_ae_invoice_transaction_type='00000001',
                currency_id=self.env.ref('base.USD').id,
                tax=self.tax_zero_rated,
            )

        self._assert_matches_fixture(xml_tree, 'exports')

    def test_export_standard_invoice_mandatory_fields(self):
        self.company_data['company'].partner_id.write({
            'l10n_ae_registration_identifier_type': 'PAS',
            'l10n_ae_passport_issuing_country_id': self.env.ref('base.es').id,
        })

        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml()

        self._assert_matches_fixture(xml_tree, 'standard_invoice_mandatory_fields')

    def test_export_summary_tax_invoice(self):
        payment_term = self.env['account.payment.term'].create({
            'name': 'Monthly billing',
            'l10n_ae_billing_frequency': 'MTH',
        })

        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(
                l10n_ae_invoice_transaction_type='00010000',
                invoice_payment_term_id=payment_term.id,
            )

        self._assert_matches_fixture(xml_tree, 'summary_tax_invoice')

    def test_export_free_trade_zone(self):
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(
                l10n_ae_invoice_transaction_type='10000000',
                l10n_ae_beneficiary_id='189098765401003',
            )

        self._assert_matches_fixture(xml_tree, 'free_trade_zone')

    def test_export_disclosed_agent_billing(self):
        # BTAE-14 Principal ID: ibr-137-ae requires a dedicated SellerSupplierParty block (not
        # AccountingSupplierParty/PartyIdentification) when the agent bills on the principal's
        # behalf.
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(
                l10n_ae_invoice_transaction_type='00000100',
                l10n_ae_principal_id='155667745601003',
            )

        self._assert_matches_fixture(xml_tree, 'disclosed_agent_billing')

    def test_export_disclosed_agent_billing_credit_note(self):
        # Same SellerSupplierParty requirement as test_export_disclosed_agent_billing, but on a
        # credit note with a BillingReference back to the original invoice.
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00002',
                l10n_ae_invoice_transaction_type='00000100',
                l10n_ae_principal_id='155667745601003',
                post=True,
            )
            credit_note = self._reverse_invoice(invoice, post=True, l10n_ae_credit_note_reason='DL8.61.1.E')

            xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(credit_note)
            self.assertFalse(errors)
            xml_tree = self.get_xml_tree_from_string(xml_content)
            uuid_node = xml_tree.find('.//{*}UUID')
            if uuid_node is not None:
                uuid_node.text = '___ignore___'

        self._assert_matches_fixture(xml_tree, 'disclosed_agent_billing_credit_note')

    def test_export_service_line(self):
        # ibr-185-ae: Service accounting code (BTAE-17, cac:AdditionalItemIdentification with
        # schemeID='SAC') is mandatory when Item type (BTAE-13) is 'Services'.
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(product=self.product_service)

        self._assert_matches_fixture(xml_tree, 'service_line')

    def test_export_supply_through_e_commerce(self):
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(l10n_ae_invoice_transaction_type='00000010')

        self._assert_matches_fixture(xml_tree, 'e_commerce')

    def test_export_zero_rated_supplies(self):
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(tax=self.tax_zero_rated)

        self._assert_matches_fixture(xml_tree, 'zero_rated_supplies')

    def test_export_continuous_supply(self):
        # Same 0% zero-rated tax as Zero Rated Supplies - only the transaction type flag differs.
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(
                l10n_ae_invoice_transaction_type='00001000',
                tax=self.tax_zero_rated,
            )

        self._assert_matches_fixture(xml_tree, 'continuous_supply')

    def test_export_self_billing_invoice(self):
        # Odoo's own generic self-billing mechanism (a vendor bill exported as a UBL
        # self-invoice on the buyer's behalf) - document type is derived purely from
        # move_type ('in_invoice' -> 'self_invoice'), independent of any AE-specific field.
        # See account_edi_ubl.py's _ubl_add_values_document_type.
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(move_type='in_invoice')

        self._assert_matches_fixture(xml_tree, 'self_billing_invoice')

    def test_export_self_billing_credit_note(self):
        with freeze_time('2025-03-05'):
            xml_tree = self._generate_invoice_xml(move_type='in_refund', l10n_ae_credit_note_reason='VD')

        self._assert_matches_fixture(xml_tree, 'self_billing_credit_note')

    def test_export_exempt_tax_requires_exemption_reason_code(self):
        # ibr-167-ae: category 'E' MUST carry an exemption reason code, and l10n_ae's exempt
        # taxes ship without one - the export must refuse instead of emitting rejected XML.
        tax_exempt = self.env['account.chart.template'].ref('uae_sale_tax_exempted')
        self.assertEqual(tax_exempt.ubl_cii_tax_category_code, 'E')
        tax_exempt.ubl_cii_tax_exemption_reason_code = False

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=tax_exempt)],
                name='INV/2025/00001',
                post=True,
            )
        _xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
        self.assertTrue(
            any('Tax Exemption Reason Code' in error for error in errors),
            f"Exempt tax without a reason code should block the export, got: {errors}",
        )

    def test_export_exempt_tax_omits_vat_rate(self):
        # aligned-ibrp-e-05 (line) and ibr-121-ae (breakdown): no VAT rate on category 'E',
        # the opposite of EN16931's BR-E-05, which wants it present and equal to 0.
        tax_exempt = self.env['account.chart.template'].ref('uae_sale_tax_exempted')
        tax_exempt.ubl_cii_tax_exemption_reason_code = 'DL8.46.3'

        # A standard-rated line alongside the exempt one, both because ibr-151-ae refuses a tax
        # invoice made up of nothing but exempt lines, and because it pins the suppression to
        # category 'E' instead of every category.
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[
                    self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a),
                    self._prepare_invoice_line(product_id=self.product_a, tax_ids=tax_exempt),
                ],
                name='INV/2025/00001',
                post=True,
            )
        xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
        self.assertFalse(errors)
        xml_tree = self.get_xml_tree_from_string(xml_content)

        seen = set()
        for tag in ('ClassifiedTaxCategory', 'TaxCategory'):
            for node in xml_tree.findall(f'.//{{*}}{tag}'):
                category = node.findtext('{*}ID')
                seen.add(category)
                if category == 'E':
                    self.assertIsNone(
                        node.find('{*}Percent'),
                        f"{tag} for category 'E' must not carry a VAT rate (aligned-ibrp-e-05 / ibr-121-ae)",
                    )
                    self.assertEqual(node.findtext('{*}TaxExemptionReasonCode'), 'DL8.46.3')
                else:
                    self.assertIsNotNone(node.find('{*}Percent'), f"{tag} for '{category}' should keep its rate")
        self.assertEqual(seen, {'S', 'E'})

    def test_export_exempt_document_level_allowance_keeps_vat_rate(self):
        # aligned-ibrp-e-06/e-07: document level allowances and charges with category 'E' need
        # the rate kept at 0 - the opposite of the line and breakdown rules above. Guards
        # against suppressing it in the grouping key, which feeds all three node types.
        tax_category = {
            'currency': self.env.ref('base.AED'),
            'tax_category_code': 'E',
            'percent': 0.0,
            'scheme_id': 'VAT',
        }
        handler = self.env['account.edi.xml.pint_ae']

        allowance_node = handler._ubl_get_allowance_charge_global_discount_tax_category_node({}, tax_category)
        self.assertEqual(allowance_node['cbc:Percent']['_text'], 0.0)

        for node in (
            handler._ubl_get_line_item_node_classified_tax_category_node({}, tax_category),
            handler._ubl_get_tax_category_node({}, tax_category),
        ):
            self.assertIsNone(node['cbc:Percent']['_text'])

    def test_export_tax_invoice_with_only_exempt_lines_is_refused(self):
        # ibr-151-ae: a 380/381 document needs at least one line that is neither 'E' nor 'O' -
        # a wholly exempt supply belongs on a commercial invoice (480/81).
        tax_exempt = self.env['account.chart.template'].ref('uae_sale_tax_exempted')
        tax_exempt.ubl_cii_tax_exemption_reason_code = 'DL8.46.3'

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=tax_exempt)],
                name='INV/2025/00001',
                post=True,
            )
        _xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
        self.assertTrue(
            any('not exempt from VAT' in error for error in errors),
            f"A tax invoice with only exempt lines should be refused, got: {errors}",
        )

    def test_export_commercial_invoice_with_only_exempt_lines_is_allowed(self):
        # Counterpart of the above: ibr-151-ae only applies to 380/381, so the same lines on a
        # commercial invoice (480) must still export.
        tax_exempt = self.env['account.chart.template'].ref('uae_sale_tax_exempted')
        tax_exempt.ubl_cii_tax_exemption_reason_code = 'DL8.46.3'

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=tax_exempt)],
                name='INV/2025/00001',
                l10n_ae_invoice_type='commercial',
                post=True,
            )
        _xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
        self.assertFalse(errors)
