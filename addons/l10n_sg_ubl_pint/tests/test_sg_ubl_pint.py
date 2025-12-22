# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import file_open
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSgUBLPint(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sg')
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')

        # TIN number is required
        cls.company_data['company'].write({
            'vat': '197401143C',
            'l10n_sg_unique_entity_number': '201131415A',
            'street': 'Tyersall Avenue',
            'zip': '248048',
            'city': 'Central Singapore',
            'phone': '+65 9123 4567',
        })
        cls.partner_a.write({
            'vat': 'S16FC0121D',
            'country_id': cls.env.ref('base.sg').id,
            'street': 'that other street, 3',
            'zip': '248050',
            'city': 'East Singapore',
            'phone': '+65 9123 4589',
        })
        cls.tax_9 = cls.env['account.tax'].create({
            'name': '9% GST',
            'amount_type': 'percent',
            'amount': 9,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.sg').id,
            'ubl_cii_tax_category_code': 'SR',
        })

        cls.fakenow = datetime(2024, 7, 15, 10, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_invoice(self):
        invoice = self.init_invoice('out_invoice', currency=self.other_currency, products=self.product_a, taxes=self.tax_9)
        invoice.action_post()

        actual_xml, errors = self.env['account.edi.xml.pint_sg']._export_invoice(invoice)
        self.assertFalse(errors)

        with file_open('l10n_sg_ubl_pint/tests/expected_xmls/invoice.xml', 'rb') as f:
            expected_xml = f.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml),
        )
