# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import file_open
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyUBLPint(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')

        # TIN number is required
        cls.company_data['company'].write({
            'vat': 'C2584563200',
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that one street, 5',
            'city': 'Main city',
            'phone': '+60123456789',
        })
        cls.partner_a.write({
            'vat': 'C2584563201',
            'country_id': cls.env.ref('base.my').id,
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that other street, 3',
            'city': 'Main city',
            'phone': '+60123456786',
        })

        cls.fakenow = datetime(2024, 7, 15, 10, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_invoice_no_taxes(self):
        invoice = self.init_invoice('out_invoice', products=self.product_a, taxes=[])
        invoice.action_post()

        actual_xml, errors = self.env['account.edi.xml.pint_my']._export_invoice(invoice)
        self.assertFalse(errors)

        with file_open('l10n_my_ubl_pint/tests/expected_xmls/invoice_no_taxes.xml', 'rb') as f:
            expected_xml = f.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    def test_invoice_with_sst(self):
        invoice = self.init_invoice('out_invoice', currency=self.other_currency, products=self.product_a)

        invoice.write({
            'invoice_incoterm_id': self.env.ref('account.incoterm_CFR').id,
        })

        self.company_data['company'].write({
            'sst_registration_number': 'A01-2345-67891012',
            'ttx_registration_number': '123-4567-89012345',
        })
        self.partner_a.commercial_partner_id.sst_registration_number = 'A01-2345-67891013'

        invoice.action_post()

        actual_xml, errors = self.env['account.edi.xml.pint_my']._export_invoice(invoice)
        self.assertFalse(errors)

        with file_open('l10n_my_ubl_pint/tests/expected_xmls/invoice_with_sst.xml', 'rb') as f:
            expected_xml = f.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml),
        )
