from unittest.mock import patch

from freezegun import freeze_time
from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_path

from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestExportPintAe(TestUblCiiCommon):

    @classmethod
    @TestUblCiiCommon.setup_country('ae')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].partner_id.write({
            'peppol_endpoint': '9900000097',
            'peppol_eas': '0235',
            'street': 'Al Maktoum Road',
            'city': 'Dubai',
            'zip': '00000',
            'state_id': cls.env.ref('base.state_ae_du').id,
            # A TRN, else the Peppol endpoint is exported as tax scheme (ibr-133-ae, ibr-148-ae).
            'vat': '100099099000003',
            'l10n_ae_registration_identifier': '112345678900001',
            'l10n_ae_registration_identifier_type': 'TL',
            'l10n_ae_authority_name': 'Trade License issuing Authority',
        })

        cls.partner_ae = cls.env['res.partner'].create({
            **cls._create_partner_default_values(),
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

        cls.tax_zero_rated = cls.env['account.chart.template'].ref('uae_sale_tax_0')
        cls.tax_out_of_scope = cls.env['account.chart.template'].ref('uae_out_of_scope')

        # ibr-184-ae: a Goods line needs an HS code.
        cls.product_a.l10n_ae_hs_code = '7214'

        # ibr-185-ae: a Services line needs a service accounting code.
        cls.product_service = cls.env['product.product'].create({
            'name': 'product_service',
            'type': 'service',
            'lst_price': 100.0,
            'l10n_ae_service_accounting_code': '998596',
        })

        # A vendor bill is only exported as a self-billed invoice from a self-billing journal.
        cls.self_billing_journal = cls.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })

    @classmethod
    def _create_company(cls, **create_values):
        # EXTENDS 'account_edi_ubl_cii': keep the AED of the AE chart instead of its EUR default.
        create_values.setdefault('currency_id', cls.env.ref('base.AED').id)
        return super()._create_company(**create_values)

    def _get_test_file_path(self, file_name, subfolder=''):
        # EXTENDS 'account': the expected files all live in tests/expected_xml.
        return file_path(f'{self.test_module}/tests/expected_xml/{file_name}')

    def test_export_invoice(self):
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'standard_tax_invoice')

    def test_export_commercial_invoice(self):
        """ aligned-ibrp-o-09: a commercial invoice carries no VAT, category 'O' at 0%. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_out_of_scope)],
                name='INV/2025/00001',
                l10n_ae_invoice_type='commercial',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'commercial_invoice')

    def test_export_exports(self):
        """ 1 USD = 3.6725 AED. The buyer isn't on Peppol: the predefined endpoint 0235:9900000099.

        The rate is created here, not in setUpClass: any foreign rate in the company changes the
        tax rounding of the AED-only tests too.
        """
        self.env['res.currency.rate'].create({
            'name': '2025-01-01',
            'rate': 1 / 3.6725,
            'currency_id': self.env.ref('base.USD').id,
            'company_id': self.company_data['company'].id,
        })

        with freeze_time('2025-03-05'), patch.object(type(self.env['res.partner']), '_get_peppol_verification_state', return_value='not_valid'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_zero_rated)],
                name='INV/2025/00001',
                l10n_ae_transaction_type_ids=[Command.set(self.env.ref('l10n_ae_ubl_pint.transaction_type_exports').ids)],
                currency_id=self.env.ref('base.USD').id,
                post=True,
            )
            self.partner_ae.button_account_peppol_check_partner_endpoint()
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'exports')

    def test_export_standard_invoice_mandatory_fields(self):
        self.company_data['company'].partner_id.write({
            'l10n_ae_registration_identifier_type': 'PAS',
            'l10n_ae_passport_issuing_country_id': self.env.ref('base.es').id,
        })

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'standard_invoice_mandatory_fields')

    def test_export_summary_tax_invoice(self):
        payment_term = self.env['account.payment.term'].create({
            'name': 'Monthly billing',
            'l10n_ae_billing_frequency': 'MTH',
        })

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                l10n_ae_transaction_type_ids=[Command.set(self.env.ref('l10n_ae_ubl_pint.transaction_type_summary').ids)],
                invoice_payment_term_id=payment_term.id,
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'summary_tax_invoice')

    def test_export_billing_frequency(self):
        """ BTAE-06 goes in the invoicing period, which then needs a start or end date (ibr-co-19). """
        payment_term = self.env['account.payment.term'].create({
            'name': 'Other billing',
            'l10n_ae_billing_frequency': 'OTH',
        })

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                invoice_payment_term_id=payment_term.id,
            )

            # [ibr-160-ae] "Others" has to be described in the invoice note (IBT-022).
            self.assertEqual(set(self.env['account.move.send']._l10n_ae_pint_get_alerts(invoice, '')), {'l10n_ae_pint_move_billing_frequency_note_missing'})
            invoice.narration = "Billed every 10 days"
            self.assertFalse(self.env['account.move.send']._l10n_ae_pint_get_alerts(invoice, ''))

            invoice.action_post()
            xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
            self.assertFalse(errors)
            tree = etree.fromstring(xml_content)
            self.assertEqual(tree.findtext('{*}InvoicePeriod/{*}StartDate'), '2025-03-05')
            self.assertEqual(tree.findtext('{*}InvoicePeriod/{*}EndDate'), '2025-03-05')
            self.assertEqual(tree.findtext('{*}InvoicePeriod/{*}DescriptionCode'), 'OTH')
            self.assertIsNone(tree.find('{*}InvoicePeriod/{*}Description'))
            self.assertEqual(tree.findtext('{*}Note'), "Billed every 10 days")

    def test_export_free_trade_zone(self):
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                l10n_ae_transaction_type_ids=[Command.set(self.env.ref('l10n_ae_ubl_pint.transaction_type_free_trade_zone').ids)],
                l10n_ae_beneficiary_id='189098765401003',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'free_trade_zone')

    def test_export_disclosed_agent_billing(self):
        """ ibr-137-ae: BTAE-14 Principal ID in its own SellerSupplierParty. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                l10n_ae_transaction_type_ids=[Command.set(self.env.ref('l10n_ae_ubl_pint.transaction_type_disclosed_agent_billing').ids)],
                l10n_ae_principal_id='155667745601003',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'disclosed_agent_billing')

    def test_export_service_line(self):
        """ ibr-185-ae: a Services item carries its service accounting code (BTAE-17). """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_service, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'service_line')

    def test_export_supply_through_e_commerce(self):
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                l10n_ae_transaction_type_ids=[Command.set(self.env.ref('l10n_ae_ubl_pint.transaction_type_e_commerce').ids)],
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'e_commerce')

    def test_export_zero_rated_supplies(self):
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_zero_rated)],
                name='INV/2025/00001',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'zero_rated_supplies')

    def test_export_continuous_supply(self):
        """ Same 0% tax as the zero rated supplies, only the transaction type differs. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_zero_rated)],
                name='INV/2025/00001',
                l10n_ae_transaction_type_ids=[Command.set(self.env.ref('l10n_ae_ubl_pint.transaction_type_continuous_supply').ids)],
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'continuous_supply')

    def test_export_self_billing_invoice(self):
        """ A vendor bill from a self-billing journal is exported as a self-billed invoice. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='in_invoice',
                partner_id=self.partner_ae,
                journal_id=self.self_billing_journal.id,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'self_billing_invoice')

    def test_export_exempt_tax_omits_vat_rate(self):
        """ aligned-ibrp-e-05 and ibr-121-ae: no VAT rate on category 'E', where EN16931 wants 0.

        The standard rated line keeps a tax invoice valid (ibr-151-ae) and checks only 'E' loses its rate.
        """
        tax_exempt = self.env['account.chart.template'].ref('uae_sale_tax_exempted')
        tax_exempt.ubl_cii_tax_exemption_reason_code = 'DL8.46.3'

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

    def test_export_incoterm(self):
        """ BTAE-22 in cac:Delivery/cac:DeliveryTerms, and no block at all when unset (ibr-196-ae). """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                post=True,
            )

            invoice.invoice_incoterm_id = False
            tree = etree.fromstring(self.env['account.edi.xml.pint_ae']._export_invoice(invoice)[0])
            self.assertIsNone(
                tree.find('.//{*}DeliveryTerms'),
                "No incoterm must mean no cac:DeliveryTerms block at all (ibr-196-ae).",
            )

            invoice.invoice_incoterm_id = self.env.ref('account.incoterm_CIF')
            tree = etree.fromstring(self.env['account.edi.xml.pint_ae']._export_invoice(invoice)[0])
            delivery_terms = tree.find('.//{*}Delivery/{*}DeliveryTerms')
            self.assertIsNotNone(
                delivery_terms,
                "BTAE-22 belongs under cac:Delivery, not beside it.",
            )
            self.assertEqual(delivery_terms.findtext('{*}ID'), 'CIF')

    def test_export_credit_note_with_reason(self):
        """ ibr-055-ae: a Volume Discount credit note is the one needing no preceding invoice. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_refund',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                l10n_ae_credit_note_reason='VD',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'credit_note')

    def test_export_credit_note_with_billing_reference(self):
        """ A reversal of a posted invoice, with BTAE-03 and the BillingReference to it. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00002',
                post=True,
            )
            credit_note = self._reverse_invoice(invoice, post=True, l10n_ae_credit_note_reason='DL8.61.1.A')

            self._generate_invoice_ubl_file(credit_note)
            self._assert_invoice_ubl_file(credit_note, 'credit_note_billing_reference')

    def test_export_volume_discount_credit_note_without_billing_reference(self):
        """ ibr-055-ae: a Volume Discount credit note has no BillingReference, even when it reverses an invoice. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00002',
                post=True,
            )
            credit_note = self._reverse_invoice(invoice, post=True, l10n_ae_credit_note_reason='VD')
            self.assertEqual(credit_note.reversed_entry_id, invoice)

            xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(credit_note)
            self.assertFalse(errors)
            tree = etree.fromstring(xml_content)
            self.assertIsNone(tree.find('{*}BillingReference'))
            self.assertEqual(tree.findtext('{*}DiscrepancyResponse/{*}ResponseCode'), 'VD')

    def test_export_commercial_credit_note(self):
        """ The commercial invoice reversed: category 'O', with a reason and a BillingReference (ibr-055-ae). """
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

            self._generate_invoice_ubl_file(credit_note)
            self._assert_invoice_ubl_file(credit_note, 'commercial_credit_note')

    def test_export_disclosed_agent_billing_credit_note(self):
        """ The SellerSupplierParty of a Disclosed Agent Billing, on a credit note. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00002',
                l10n_ae_transaction_type_ids=[Command.set(self.env.ref('l10n_ae_ubl_pint.transaction_type_disclosed_agent_billing').ids)],
                l10n_ae_principal_id='155667745601003',
                post=True,
            )
            credit_note = self._reverse_invoice(invoice, post=True, l10n_ae_credit_note_reason='DL8.61.1.E')

            self._generate_invoice_ubl_file(credit_note)
            self._assert_invoice_ubl_file(credit_note, 'disclosed_agent_billing_credit_note')

    def test_export_self_billing_credit_note(self):
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='in_refund',
                partner_id=self.partner_ae,
                journal_id=self.self_billing_journal.id,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                l10n_ae_credit_note_reason='VD',
                post=True,
            )
            self._generate_invoice_ubl_file(invoice)
            self._assert_invoice_ubl_file(invoice, 'self_billing_credit_note')

    def test_export_line_item_values_come_from_the_product(self):
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[
                    self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a),
                    self._prepare_invoice_line(product_id=self.product_service, tax_ids=self.tax_sale_a),
                ],
                name='INV/2025/00001',
            )
        goods_line, service_line = invoice.invoice_line_ids
        self.assertRecordValues(invoice.invoice_line_ids, [
            {'l10n_ae_item_type': 'G', 'l10n_ae_hs_code': '7214', 'l10n_ae_service_accounting_code': False},
            {'l10n_ae_item_type': 'S', 'l10n_ae_hs_code': False, 'l10n_ae_service_accounting_code': '998596'},
        ])

        # The values can be changed on the line, and the export follows the line.
        goods_line.l10n_ae_hs_code = '7215'
        service_line.write({'l10n_ae_item_type': 'B', 'l10n_ae_hs_code': '8517'})
        invoice.action_post()
        tree = etree.fromstring(self.env['account.edi.xml.pint_ae']._export_invoice(invoice)[0])
        goods_item, service_item = tree.findall('.//{*}InvoiceLine/{*}Item')
        self.assertEqual(goods_item.findtext('.//{*}ItemClassificationCode'), '7215')
        self.assertEqual(service_item.findtext('.//{*}CommodityCode'), 'B')
        self.assertEqual(service_item.findtext('.//{*}ItemClassificationCode'), '8517')
        self.assertEqual(service_item.findtext('{*}AdditionalItemIdentification/{*}ID'), '998596')

    def test_export_line_without_product(self):
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(name='Consulting', price_unit=100.0, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
            )
        line = invoice.invoice_line_ids
        self.assertFalse(line.l10n_ae_item_type)
        self.assertFalse(self.env['account.move.send']._l10n_ae_pint_get_alerts(line, ''), "A line without an item type needs no classification.")
        tree = etree.fromstring(self.env['account.edi.xml.pint_ae']._export_invoice(invoice)[0])
        self.assertIsNone(tree.find('.//{*}InvoiceLine/{*}Item/{*}CommodityClassification'))

        # Once an item type is set on the line, its code is required.
        line.l10n_ae_item_type = 'S'
        self.assertEqual(set(self.env['account.move.send']._l10n_ae_pint_get_alerts(line, '')), {'l10n_ae_pint_line_service_accounting_code_missing'})

        line.l10n_ae_service_accounting_code = '998311'
        self.assertFalse(self.env['account.move.send']._l10n_ae_pint_get_alerts(line, ''))

        invoice.action_post()
        xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
        self.assertFalse(errors)
        item = etree.fromstring(xml_content).find('.//{*}InvoiceLine/{*}Item')
        self.assertEqual(item.findtext('.//{*}CommodityCode'), 'S')
        self.assertEqual(item.findtext('{*}AdditionalItemIdentification/{*}ID'), '998311')

    def test_export_section_with_hidden_composition(self):
        """ A section with hidden composition is one line per tax and item classification: goods and
        services are not merged, each keeps its own classification.
        """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[
                    self._prepare_invoice_line(name='Bundle', display_type='line_section', collapse_composition=True, price_unit=0.0),
                    self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a),
                    self._prepare_invoice_line(product_id=self.product_service, tax_ids=self.tax_sale_a),
                ],
                name='INV/2025/00001',
                post=True,
            )
        xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
        self.assertFalse(errors)
        tree = etree.fromstring(xml_content)
        goods_item, service_item = tree.findall('.//{*}InvoiceLine/{*}Item')
        self.assertEqual(goods_item.findtext('{*}Name'), 'Bundle')
        self.assertEqual(goods_item.findtext('.//{*}CommodityCode'), 'G')
        self.assertEqual(goods_item.findtext('.//{*}ItemClassificationCode'), '7214')
        self.assertIsNone(goods_item.find('{*}AdditionalItemIdentification'))
        self.assertEqual(service_item.findtext('{*}Name'), 'Bundle')
        self.assertEqual(service_item.findtext('.//{*}CommodityCode'), 'S')
        self.assertIsNone(service_item.find('.//{*}ItemClassificationCode'))
        self.assertEqual(service_item.findtext('{*}AdditionalItemIdentification/{*}ID'), '998596')

    def test_credit_note_send_checks(self):
        def create_credit_note(**values):
            return self._create_invoice(
                move_type='out_refund',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                **values,
            )

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                post=True,
            )

            # ibr-158-ae: no reason.
            credit_note = create_credit_note()
            self.assertEqual(set(self.env['account.move.send']._l10n_ae_pint_get_alerts(credit_note, '')), {'l10n_ae_pint_move_credit_note_reason_missing'})

            # ibr-055-ae: a reason other than Volume Discount, and no preceding invoice.
            credit_note.l10n_ae_credit_note_reason = 'DL8.61.1.A'
            self.assertEqual(set(self.env['account.move.send']._l10n_ae_pint_get_alerts(credit_note, '')), {'l10n_ae_pint_move_preceding_invoice_missing'})

            # Setting "Reversal Of" by hand gives the preceding invoice reference.
            credit_note.reversed_entry_id = invoice
            self.assertFalse(self.env['account.move.send']._l10n_ae_pint_get_alerts(credit_note, ''))
            credit_note.action_post()
            xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(credit_note)
            self.assertFalse(errors)
            tree = etree.fromstring(xml_content)
            self.assertEqual(tree.findtext('{*}BillingReference/{*}InvoiceDocumentReference/{*}ID'), invoice.name)

            # Volume Discount needs no preceding invoice.
            self.assertFalse(self.env['account.move.send']._l10n_ae_pint_get_alerts(create_credit_note(l10n_ae_credit_note_reason='VD'), ''))

            # A commercial credit note (81) needs a reason too, and a preceding invoice.
            commercial_credit_note = create_credit_note(l10n_ae_invoice_type='commercial')
            self.assertEqual(
                set(self.env['account.move.send']._l10n_ae_pint_get_alerts(commercial_credit_note, '')),
                {'l10n_ae_pint_move_credit_note_reason_missing'},
            )
            commercial_credit_note.l10n_ae_credit_note_reason = 'DL8.61.1.A'
            self.assertEqual(
                set(self.env['account.move.send']._l10n_ae_pint_get_alerts(commercial_credit_note, '')),
                {'l10n_ae_pint_move_preceding_invoice_missing'},
            )
            commercial_credit_note.reversed_entry_id = invoice
            self.assertFalse(self.env['account.move.send']._l10n_ae_pint_get_alerts(commercial_credit_note, ''))

            # Self-billed credit notes are AE credit notes too.
            self_billed_credit_note = self._create_invoice(
                move_type='in_refund',
                partner_id=self.partner_ae,
                journal_id=self.self_billing_journal.id,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
            )
            self.assertEqual(
                set(self.env['account.move.send']._l10n_ae_pint_get_alerts(self_billed_credit_note, '')),
                {'l10n_ae_pint_move_credit_note_reason_missing'},
            )

    def test_export_order_reference(self):
        """ IBT-013 comes from the Customer Reference, without it there's no OrderReference. """
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                post=True,
            )
            tree = etree.fromstring(self.env['account.edi.xml.pint_ae']._export_invoice(invoice)[0])
            self.assertIsNone(tree.find('{*}OrderReference'))

            invoice.ref = 'PO-123'
            tree = etree.fromstring(self.env['account.edi.xml.pint_ae']._export_invoice(invoice)[0])
            self.assertEqual(tree.findtext('{*}OrderReference/{*}ID'), 'PO-123')

    def test_export_line_product_without_classification(self):
        """ A product without HS nor service accounting code gives no item type: no alert, no classification. """
        product_fee = self.env['product.product'].create({'name': 'Delivery fee', 'type': 'service', 'lst_price': 10.0})
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[
                    self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a),
                    self._prepare_invoice_line(product_id=product_fee, tax_ids=self.tax_sale_a),
                ],
                name='INV/2025/00001',
                post=True,
            )
        goods_line, fee_line = invoice.invoice_line_ids
        self.assertEqual(goods_line.l10n_ae_item_type, 'G')
        self.assertFalse(fee_line.l10n_ae_item_type)
        self.assertFalse(self.env['account.move.send']._l10n_ae_pint_get_alerts(invoice.invoice_line_ids, ''))

        xml_content, errors = self.env['account.edi.xml.pint_ae']._export_invoice(invoice)
        self.assertFalse(errors)
        goods_item, fee_item = etree.fromstring(xml_content).findall('{*}InvoiceLine/{*}Item')
        self.assertEqual(goods_item.findtext('.//{*}CommodityCode'), 'G')
        self.assertIsNone(fee_item.find('{*}CommodityClassification'))

    def test_invoice_type_follows_partner(self):
        """ A tax invoice for a company, a simplified one, not sent by Peppol, for an individual. """
        individual = self.env['res.partner'].create({'name': 'Walk-in customer', 'is_company': False, 'country_id': self.env.ref('base.ae').id})
        self.partner_ae.is_company = True
        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
            )
        self.assertEqual(invoice.l10n_ae_invoice_type, 'tax')

        invoice.partner_id = individual
        self.assertEqual(invoice.l10n_ae_invoice_type, 'simplified')
        self.assertFalse(self.env['account.move.send']._is_applicable_to_move('peppol', invoice))

        # A posted invoice keeps the type it was issued with.
        invoice.action_post()
        invoice.partner_id.is_company = True
        self.assertEqual(invoice.l10n_ae_invoice_type, 'simplified')

    def test_export_combined_transaction_types(self):
        """ Several transaction types set a BTAE-02 flag each. """
        TransactionType = self.env['l10n_ae.transaction.type']
        e_commerce_exports = (
            self.env.ref('l10n_ae_ubl_pint.transaction_type_e_commerce')
            | self.env.ref('l10n_ae_ubl_pint.transaction_type_exports')
        )
        self.assertEqual(e_commerce_exports._get_flags_code(), '00000011')
        self.assertEqual(TransactionType._get_from_flags_code('00000011'), e_commerce_exports)
        self.assertFalse(TransactionType.browse()._get_flags_code())

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                l10n_ae_transaction_type_ids=[Command.set(e_commerce_exports.ids)],
                post=True,
            )
        tree = etree.fromstring(self.env['account.edi.xml.pint_ae']._export_invoice(invoice)[0])
        self.assertEqual(tree.findtext('{*}ProfileExecutionID'), '00000011')

    def test_send_wizard_hides_peppol_on_simplified(self):
        self.company_data['company'].account_peppol_proxy_state = 'receiver'
        individual = self.env['res.partner'].create({'name': 'Walk-in customer', 'is_company': False, 'country_id': self.env.ref('base.ae').id})
        with freeze_time('2025-03-05'):
            tax_invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                l10n_ae_invoice_type='tax',
                post=True,
            )
            simplified_credit_note = self._create_invoice(
                move_type='out_refund',
                partner_id=individual,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                post=True,
            )
        self.assertEqual(simplified_credit_note.l10n_ae_invoice_type, 'simplified')

        def wizard_methods(move):
            wizard = self.env['account.move.send.wizard'].with_context(active_model='account.move', active_ids=move.ids).create({})
            return set(wizard.sending_method_checkboxes)

        self.assertIn('peppol', wizard_methods(tax_invoice))
        self.assertNotIn('peppol', wizard_methods(simplified_credit_note))

    def test_line_item_values_follow_product_on_draft(self):
        """ A change on the product reaches the draft lines only, like l10n_in's HSN/SAC code. """
        with freeze_time('2025-03-05'):
            posted = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                post=True,
            )
            draft = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
            )
        self.product_a.l10n_ae_hs_code = '7215'
        self.assertEqual(draft.invoice_line_ids.l10n_ae_hs_code, '7215')
        self.assertEqual(posted.invoice_line_ids.l10n_ae_hs_code, '7214')

    def test_export_billing_period_on_invoice_date(self):
        """ The payment term's frequency of billing (BTAE-06), with a single-day period on the invoice date: the
        due date is a payment deadline, not the end of the period.
        """
        payment_term = self.env.ref('account.account_payment_term_15days')
        self.assertEqual(payment_term.l10n_ae_billing_frequency, 'Q15')

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
                name='INV/2025/00001',
                invoice_payment_term_id=payment_term.id,
                post=True,
            )
        self.assertEqual(str(invoice.invoice_date_due), '2025-03-20')
        tree = etree.fromstring(self.env['account.edi.xml.pint_ae']._export_invoice(invoice)[0])
        self.assertEqual(tree.findtext('{*}InvoicePeriod/{*}StartDate'), '2025-03-05')
        self.assertEqual(tree.findtext('{*}InvoicePeriod/{*}EndDate'), '2025-03-05')
        self.assertEqual(tree.findtext('{*}InvoicePeriod/{*}DescriptionCode'), 'Q15')

    def test_transaction_type_exports_from_fiscal_position(self):
        """ A fiscal position that isn't for the UAE makes the invoice an export by default. """
        ChartTemplate = self.env['account.chart.template']
        non_uae = ChartTemplate.ref('account_fiscal_position_non_uae_countries')
        uae = ChartTemplate.ref('account_fiscal_position_uae')
        exports = self.env.ref('l10n_ae_ubl_pint.transaction_type_exports')
        e_commerce = self.env.ref('l10n_ae_ubl_pint.transaction_type_e_commerce')

        with freeze_time('2025-03-05'):
            invoice = self._create_invoice(
                move_type='out_invoice',
                partner_id=self.partner_ae,
                invoice_line_ids=[self._prepare_invoice_line(product_id=self.product_a, tax_ids=self.tax_sale_a)],
            )
        invoice.write({'fiscal_position_id': uae.id, 'l10n_ae_transaction_type_ids': [Command.set(e_commerce.ids)]})
        self.assertEqual(invoice.l10n_ae_transaction_type_ids, e_commerce)

        # Exports is added next to the types already set.
        invoice.fiscal_position_id = non_uae
        self.assertEqual(invoice.l10n_ae_transaction_type_ids, e_commerce | exports)

        # Back to a UAE fiscal position: the types are left as they are.
        invoice.fiscal_position_id = uae
        self.assertEqual(invoice.l10n_ae_transaction_type_ids, e_commerce | exports)
