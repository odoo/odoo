# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import file_open
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestJpUBLPint(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', 'False')
        cls.other_currency = cls.setup_other_currency('USD')

        # TIN number is required
        cls.company_data['company'].write({
            'vat': '7482543580381',
            'street': '池上通り',
            'zip': '140-0004',
            'city': '品川区',
            'state_id': cls.env.ref('base.state_jp_jp-19').id,
            'phone': '+81 90-1234-5678',
        })
        cls.partner_a.write({
            'vat': 'T7000012050002',
            'street': '3F 星和池袋ビル',
            'zip': '170-0013',
            'city': '豊島区',
            'state_id': cls.env.ref('base.state_jp_jp-13').id,
            'country_id': cls.env.ref('base.jp').id,
            'phone': '+81 3-5798-5555',
        })

        cls.fakenow = datetime(2024, 7, 15, 10, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_invoice(self):
        invoice = self.init_invoice('out_invoice', currency=self.other_currency, products=self.product_a)
        invoice.action_post()

        actual_xml, errors = self.env['account.edi.xml.pint_jp']._export_invoice(invoice)
        self.assertFalse(errors)

        with file_open('l10n_jp_ubl_pint/tests/expected_xmls/invoice.xml', 'rb') as f:
            expected_xml = f.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    def test_invoice_new(self):
        self.env['ir.config_parameter'].set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', 'True')
        self.test_invoice()
