from freezegun import freeze_time
from odoo import Command

from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLTR(TestUBLTRCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].partner_id.write({'l10n_tr_tax_office_id': cls.env.ref("l10n_tr.tax_office_1009").id})
        cls.einvoice_partner.write({'l10n_tr_tax_office_id': cls.env.ref("l10n_tr.tax_office_1009").id})

        cls.tax_0 = cls.env['account.chart.template'].ref('tr_s_0_ex')
        cls.tax_20 = cls.env['account.chart.template'].ref('tr_s_20')
        cls.tax_20_withholding = cls.env['account.chart.template'].ref('tr_s_wh_20_9_10')
        cls.fiscal_position_withholding = cls.env['account.chart.template'].ref('tr_fp_wh_9_10')

        # Withholding Reason (9/10 - Private Security Service)
        cls.reason_607 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice.account_tax_code_607')
        # Registered for Export Reason
        cls.reason_701 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice.account_tax_code_701')
        cls.reason_702 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice.account_tax_code_702')

        # Tax Exemption Reason
        cls.reason_212 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice.account_tax_code_212')

        # Export Reason
        cls.reason_301 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice.account_tax_code_301')

        # Line Level Zero Tax Exemption Reason
        cls.reason_351 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice.account_tax_code_351')
        cls.incoterm = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice.incoterm_DAF')

    def test_xml_invoice_basic_export_registered_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.einvoice_partner, l10n_tr_gib_invoice_type="IHRACKAYITLI", l10n_tr_exemption_code_id=self.reason_701.id)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_export_registered_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_sale_earchive(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.earchive_partner)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_sale_earchive.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_sale_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.einvoice_partner)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_sale_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_return_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_return_invoice_xml(self.einvoice_partner)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_return_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_sale_zero_export_vat_line_einvoice(self):
        with freeze_time('2025-03-05'):
            invoice_line_ids = [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 50.00,
                    'quantity': 3,
                    'discount': 12,
                    'tax_ids': [Command.set(self.tax_0.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100.00,
                    'quantity': 3,
                    'discount': 10,
                    'tax_ids': [Command.set(self.tax_20.ids)],
                }),
            ]
            generated_xml = self._generate_invoice_xml(self.einvoice_partner, l10n_tr_gib_invoice_type="SATIS", invoice_line_ids=invoice_line_ids)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_sale_zero_export_vat_line_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_tax_exempt_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.einvoice_partner, l10n_tr_gib_invoice_type="ISTISNA", l10n_tr_exemption_code_id=self.reason_212.id)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_tax_exempt_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_withholding_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(
                self.einvoice_partner,
                self.tax_20_withholding,
                l10n_tr_gib_invoice_type="TEVKIFAT",
                fiscal_position_id=self.fiscal_position_withholding.id,
                l10n_tr_exemption_code_id=self.reason_607.id,
            )

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_withholding_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_withholding_return_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_return_invoice_xml(
                self.einvoice_partner,
                self.tax_20_withholding,
                l10n_tr_gib_invoice_type="TEVKIFAT",
                fiscal_position_id=self.fiscal_position_withholding.id,
                l10n_tr_exemption_code_id=self.reason_607.id,
            )

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_return_basic_withholding_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_earchive_multicurrency(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.earchive_partner, currency_id=self.env.ref('base.USD').id)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_earchive_multicurrency.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_einvoice_multicurrency(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(partner_id=self.einvoice_partner, currency_id=self.env.ref('base.USD').id)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_einvoice_multicurrency.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_exchange_rate_eur_try_with_usd_company_currency(self):
        with freeze_time('2025-03-05'):
            company = self.company_data['company']
            usd = self.env.ref('base.USD')
            eur = self.env.ref('base.EUR')
            eur.active = True
            try_currency = self.env.ref('base.TRY')
            company.currency_id = usd
            usd.rate_ids.unlink()
            # The rate of 1 EUR = 1.25 USD is meant to simplify tests
            self.env['res.currency.rate'].create({
                'name': '2025-03-03',
                'rate': 0.8,
                'currency_id': eur.id,
                'company_id': company.id,
            })
            self.env['res.currency.rate'].create({
                'name': '2025-03-03',
                'rate': 40.0,
                'currency_id': try_currency.id,
                'company_id': company.id,
            })
            generated_xml = self._generate_invoice_xml(partner_id=self.einvoice_partner, currency_id=eur.id)

        xml_tree = self.get_xml_tree_from_string(generated_xml)
        pricing_exchange_rate = xml_tree.find('.//{*}PricingExchangeRate/{*}CalculationRate')
        self.assertIsNotNone(pricing_exchange_rate, 'PricingExchangeRate node was not generated')
        self.assertAlmostEqual(float(pricing_exchange_rate.text), 50.0)

    def test_xml_invoice_export_earchive(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.earchive_partner, l10n_tr_is_export_invoice=True, l10n_tr_exemption_code_id=self.reason_301.id, l10n_tr_shipping_type="1", invoice_incoterm_id=self.incoterm.id)

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_export_earchive.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_export_ipac_einvoice(self):
        with freeze_time('2026-01-20'):
            generated_xml = self._generate_invoice_xml(
                self.einvoice_partner,
                l10n_tr_exemption_code_id=self.reason_702.id,
                l10n_tr_gib_invoice_type="IHRACKAYITLI",
                invoice_line_data={
                    'l10n_tr_ctsp_number': '129392930912',
                    'l10n_tr_customer_line_code': '11223345690',
                },
            )

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_export_ipac_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_import_invoice_basic_sale_einvoice_discounts(self):
        invoice = self.env["account.move"].create({"move_type": "out_invoice"})

        with file_open("l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_sale_einvoice.xml", "rb") as xml_file:
            tree = self.get_xml_tree_from_string(xml_file.read())

        self.env["account.edi.xml.ubl.tr"]._import_fill_invoice(invoice, tree, 1)

        product_line = invoice.invoice_line_ids.filtered(lambda l: l.name == 'product_a')[:1]
        global_discount_line = invoice.invoice_line_ids.filtered(lambda l: l.name == "Discount")[:1]

        self.assertEqual(product_line.discount, 12.0)
        self.assertFalse(global_discount_line, "Nilvera moves should not have any global discount line")

    def test_xml_invoice_earchive_ecommerce_sale_without_transfer(self):
        with freeze_time('2025-03-05'):
            invoice = self._generate_invoice(
                partner_id=self.earchive_partner,
                l10n_tr_sales_type='website',
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.service_product.id,
                        'price_unit': 150.0,
                        'quantity': 1,
                        'tax_ids': [Command.set(self.tax_20.ids)],
                    }),
                ],
            )
            self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'payment_method_line_id': self.inbound_payment_method_line.id})\
            ._create_payments()
            generated_xml = self.env['account.edi.xml.ubl.tr']._export_invoice(invoice)[0]

        with file_open('l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_earchive_ecommerce_sale_without_transfer.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))
