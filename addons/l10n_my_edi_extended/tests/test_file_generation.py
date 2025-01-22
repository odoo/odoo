# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time
from lxml import etree

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_my_edi.tests.test_file_generation import NS_MAP
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMyEDITestFileGeneration(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()

        # TIN number is required
        cls.company_data['company'].write({
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
            'l10n_my_edi_industrial_classification': cls.env['l10n_my_edi.industry_classification'].search([('code', '=', '01111')]).id,
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that one street, 5',
            'city': 'Main city',
            'phone': '+60123456789',
        })
        cls.partner_b.write({
            'vat': '123456789',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': 'NA',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_1'),
            'street': 'that other street, 3',
            'city': 'Main city',
            'phone': '+60123456785',
            'l10n_my_edi_malaysian_tin': 'EI00000000020',
            'l10n_my_edi_industrial_classification': cls.env.ref('l10n_my_edi.class_00000', raise_if_not_found=False).id,
        })
        cls.product_a.l10n_my_edi_classification_code = "001"

        cls.purchase_tax = cls.env['account.tax'].create({
            'name': 'tax_10',
            'amount_type': 'percent',
            'amount': 10,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.my').id,
        })

    @freeze_time('2024-07-15 10:00:00')
    def test_07_self_billing(self):
        bill = self.init_invoice(
            'in_invoice', partner=self.partner_b, products=self.product_a, taxes=self.purchase_tax,
        )
        bill.action_post()

        file, errors = bill._l10n_my_edi_generate_invoice_xml()
        self.assertFalse(errors)
        self.assertTrue(file)

        root = etree.fromstring(file)
        # We assert that the supplier is the partner of the invoice, with all information present.
        supplier_root = root.xpath('cac:AccountingSupplierParty/cac:Party', namespaces=NS_MAP)[0]
        data_to_check = [
            ('cac:PartyIdentification/cbc:ID[@schemeID="TIN"]', self.partner_b.commercial_partner_id.l10n_my_edi_malaysian_tin),  # We set the generic VAT in the new field, it should have been used.
            ('cac:PartyIdentification/cbc:ID[@schemeID="BRN"]', self.partner_b.commercial_partner_id.l10n_my_identification_number),
            ('cbc:IndustryClassificationCode', self.partner_b.commercial_partner_id.l10n_my_edi_industrial_classification.code),  # It should use the code on the partner.
            ('cac:PartyName/cbc:Name', self.partner_b.name),
        ]
        for path, expected_value in data_to_check:
            self._assert_node_values(supplier_root, path, expected_value)
        # And that the customer is the company.
        customer_root = root.xpath('cac:AccountingCustomerParty/cac:Party', namespaces=NS_MAP)[0]
        data_to_check = [
            ('cac:PartyIdentification/cbc:ID[@schemeID="TIN"]', self.company_data['company'].vat),  # We didn't set the new field as the company is malaysian, the vat should be in use.
            ('cac:PartyIdentification/cbc:ID[@schemeID="BRN"]', self.company_data['company'].l10n_my_identification_number),
            ('cac:PartyName/cbc:Name', self.company_data['company'].name),
        ]
        for path, expected_value in data_to_check:
            self._assert_node_values(customer_root, path, expected_value)

    def _assert_node_values(self, root, node_path, text, attributes=None):
        node = root.xpath(node_path, namespaces=NS_MAP)

        assert node, f'The requested node has not been found: {node_path}'

        self.assertEqual(
            node[0].text,
            text,
        )
        if attributes:
            for attribute, value in attributes.items():
                self.assertEqual(
                    node[0].attrib[attribute],
                    value,
                )
