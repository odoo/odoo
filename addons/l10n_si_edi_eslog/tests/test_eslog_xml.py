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
        #cls.env.company.partner_id.l10n_hr_business_unit_code = '12345'

    def test_export_invoice_from_account_edi_xml_eslog(self):
        """
        Test content of a generated basic invoice in Slovenian eSlog format.
        """
        self.setup_partner_as_si(self.env.company.partner_id)
        self.setup_partner_as_si_alt(self.partner_a)
        tax = self.env['account.chart.template'].ref('gd_taxr_3')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'l10n_si_reference_type': 'ON',
            'ref': '123456',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        actual_content, _dummy = self.env['account.edi.xml.eslog'].with_context(lang='en_US')._export_invoice(invoice)

        #with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice.xml', 'wb') as file:
        #    #expected_content = file.write(actual_content)
        #    file.write(actual_content)
        #    file.close()

        #with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice.xml', 'rb') as file:
        #    expected_content = file.read()
        #self.assertXmlTreeEqual(
        #    self.get_xml_tree_from_string(actual_content),
        #    self.get_xml_tree_from_string(expected_content),
        #)
