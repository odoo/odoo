from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLTR(TestUBLTRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].partner_id.write({'l10n_tr_tax_office_id': cls.env.ref("l10n_tr_nilvera_einvoice_extended.l10n_tr_nilvera_einvoice_extended_tax_office_1009").id})
        cls.einvoice_partner.write({'l10n_tr_tax_office_id': cls.env.ref("l10n_tr_nilvera_einvoice_extended.l10n_tr_nilvera_einvoice_extended_tax_office_1009").id})

        cls.tax_20 = cls.env['account.chart.template'].ref('tr_s_20')
        cls.tax_20_withholding = cls.env['account.chart.template'].ref('tr_s_vat_wh_20_OGH')
        # Registered for Export Reason
        cls.reason_701 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice_extended.l10n_tr_nilvera_einvoice_extended_account_tax_code_701')

        # Tax Exemption Reason
        cls.reason_212 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice_extended.l10n_tr_nilvera_einvoice_extended_account_tax_code_212')

        # Export Reason
        cls.reason_301 = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice_extended.l10n_tr_nilvera_einvoice_extended_account_tax_code_301')
        cls.incoterm = cls.env['account.chart.template'].ref('l10n_tr_nilvera_einvoice_extended.incoterm_DAF')

    def test_xml_invoice_basic_export_registered_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.einvoice_partner, l10n_tr_gib_invoice_type="IHRACKAYITLI", l10n_tr_exemption_code_id=self.reason_701.id)

        with file_open('l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_export_registered_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_sale_earchive(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.earchive_partner)

        with file_open('l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_sale_earchive.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_sale_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.einvoice_partner)

        with file_open('l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_sale_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_tax_exempt_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.einvoice_partner, l10n_tr_gib_invoice_type="ISTISNA", l10n_tr_exemption_code_id=self.reason_212.id)

        with file_open('l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_tax_exempt_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_withholding_einvoice(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.einvoice_partner, self.tax_20_withholding, l10n_tr_gib_invoice_type="TEVKIFAT")

        with file_open('l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_withholding_einvoice.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_earchive_multicurrency(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.earchive_partner, currency_id=self.env.ref('base.USD').id)

        with file_open('l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_earchive_multicurrency.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_einvoice_multicurrency(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(partner_id=self.einvoice_partner, currency_id=self.env.ref('base.USD').id)

        with file_open('l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_einvoice_multicurrency.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_export_earchive(self):
        with freeze_time('2025-03-05'):
            generated_xml = self._generate_invoice_xml(self.earchive_partner, l10n_tr_is_export_invoice=True, l10n_tr_exemption_code_id=self.reason_301.id, l10n_tr_shipping_type="1", invoice_incoterm_id=self.incoterm.id)

        with file_open('l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_export_earchive.xml', 'rb') as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))
