from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_si_edi_eslog.tests.test_eslog_common import TestL10nSiEslogCommon
from odoo.tests import tagged
from odoo.tools import misc

from lxml import etree


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nSiEslogXsd(TestL10nSiEslogCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_export_invoice_from_account_edi_xsd_eslog_simple(self):
        """
        Test content of a generated basic invoice in Slovenian eSlog format.
        """
        self.setup_partner_as_si(self.env.company.partner_id)
        self.setup_partner_as_si_alt(self.partner_a)

        invoice = self.create_move(params={'product': self.product_a})
        actual_content, _dummy = self.env['account.edi.xml.eslog'].with_context(lang='en_US')._export_invoice(invoice)
        xsd_schema_file_path = misc.file_path(f'addons/{self.test_module}/tests/xsd/eSLOG20_INVOIC_v200.xsd')
        xsd_root = etree.parse(xsd_schema_file_path)
        schema = etree.XMLSchema(xsd_root)
        xml_root = etree.fromstring(actual_content)
        schema.assertValid(xml_root)

    def test_export_invoice_from_account_edi_xsd_eslog_taxes(self):
        """
        Test content of a generated basic invoice in Slovenian eSlog format.
        """
        self.setup_partner_as_si(self.env.company.partner_id)
        self.setup_partner_as_si_alt(self.partner_a)
        taxes = [
            self.env['account.chart.template'].ref('gd_taxr_1'),
            self.env['account.chart.template'].ref('gd_taxr_2'),
            self.env['account.chart.template'].ref('gd_taxr_3'),
        ]

        invoice = self.create_move(params={'taxes': taxes})
        actual_content, _dummy = self.env['account.edi.xml.eslog'].with_context(lang='en_US')._export_invoice(invoice)
        xsd_schema_file_path = misc.file_path(f'addons/{self.test_module}/tests/xsd/eSLOG20_INVOIC_v200.xsd')
        xsd_root = etree.parse(xsd_schema_file_path)
        schema = etree.XMLSchema(xsd_root)
        xml_root = etree.fromstring(actual_content)
        schema.assertValid(xml_root)

    def UNUSED_test_eslog_sample_xml_vs_xsd(self):
        with misc.file_open(f'addons/{self.test_module}/tests/xsd/sample_eSLOG20_INVOIC_v200.xml', 'rb') as file:
            sample_content = file.read()
        xsd_schema_file_path = misc.file_path(f'addons/{self.test_module}/tests/xsd/eSLOG20_INVOIC_v200.xsd')
        xsd_root = etree.parse(xsd_schema_file_path)
        schema = etree.XMLSchema(xsd_root)
        xml_root = etree.fromstring(sample_content)
        schema.assertValid(xml_root)
