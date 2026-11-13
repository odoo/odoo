from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_si_edi_eslog.tests.test_eslog_common import TestL10nSiEslogCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nSiEslogXml(TestL10nSiEslogCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_export_invoice_from_account_edi_xml_eslog_simple(self):
        """
        Test content of a generated basic invoice in Slovenian eSlog format.
        """
        self.setup_partner_as_si(self.env.company.partner_id)
        self.setup_partner_as_si_alt(self.partner_a)

        invoice = self.create_move()
        actual_content, _dummy = self.env['account.edi.xml.eslog'].with_context(lang='en_US')._export_invoice(invoice)

        #with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_simple.xml', 'wb') as file:
        #    file.write(actual_content)
        #    file.close()

        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_simple.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )

    def test_export_invoice_from_account_edi_xml_eslog_taxes(self):
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

        #with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_taxes.xml', 'wb') as file:
        #    file.write(actual_content)
        #    file.close()

        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_taxes.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )
