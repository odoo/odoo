# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import file_open
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAnzUBLPint(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('au')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', 'False')
        cls.other_currency = cls.setup_other_currency('NZD')

        # TIN number is required
        cls.company_data['company'].write({
            'vat': '11225459588',
            'street': 'Henry Lawson Drive',
            'zip': '2850',
            'city': 'Home Rule',
            'state_id': cls.env.ref('base.state_au_8').id,
            'phone': '+61 412 345 678',
        })
        cls.partner_a.write({
            'vat': '49098576',
            'company_registry': '9429047488083',
            'street': 'Victoria Street',
            'zip': '3247',
            'city': 'Hamilton',
            'state_id': cls.env.ref('base.state_nz_wtc').id,
            'country_id': cls.env.ref('base.nz').id,
            'phone': '+64 21 123 4567',
        })

        cls.fakenow = datetime(2024, 7, 15, 10, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_invoice(self):
        invoice = self.init_invoice('out_invoice', currency=self.other_currency, products=self.product_a)
        invoice.action_post()

        actual_xml, errors = self.env['account.edi.xml.pint_anz']._export_invoice(invoice)
        self.assertFalse(errors)

        with file_open('l10n_anz_ubl_pint/tests/expected_xmls/invoice.xml', 'rb') as f:
            expected_xml = f.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    def test_invoice_new(self):
        self.env['ir.config_parameter'].set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', 'True')
        self.test_invoice()
