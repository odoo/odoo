# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiUblCiiTaxExtension(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.reverse_charge_tax = cls.company_data['default_tax_sale'].copy({'name': 'Reverse charge tax', 'ubl_cii_tax_category_code': 'AE', 'ubl_cii_tax_exemption_reason_code': 'VATEX-EU-AE'})
        cls.zero_rated_tax = cls.company_data['default_tax_sale'].copy({'name': 'Zero rated tax', 'ubl_cii_tax_category_code': 'Z'})
        cls.prod_tax = cls.company_data['default_tax_sale'].copy({'name': 'Production tax', 'ubl_cii_tax_category_code': 'M'})
        cls.free_export_tax = cls.company_data['default_tax_sale'].copy({'name': 'Free export tax', 'ubl_cii_tax_category_code': 'G', 'ubl_cii_tax_exemption_reason_code': 'VATEX-EU-132-1G'})
        cls.fixed_tax = cls.company_data['default_tax_sale'].copy({
            'name': 'Fixed tax',
            'ubl_cii_tax_category_code': 'E',
            'amount_type': 'fixed',
            'ubl_cii_allowance_charge_reason': 'Advertising',
            'ubl_cii_charge_reason_code': 'AA',
        })
        cls.fixed_tax2 = cls.fixed_tax.copy({
            'name': 'Fixed tax 2',
            'ubl_cii_allowance_charge_reason': 'Telecommunication',
            'ubl_cii_charge_reason_code': 'AAA',
        })

    def test_tax_subtotal(self):
        ubl_taxes = (self.reverse_charge_tax + self.zero_rated_tax + self.prod_tax + self.free_export_tax)
        # test tax by tax then with multiple taxes
        tax_list = list(ubl_taxes) + [ubl_taxes]
        for taxes in tax_list:
            invoice = self.env["account.move"].create({
                "partner_id": self.partner_a.id,
                "move_type": "out_invoice",
                "invoice_line_ids": [Command.create({"name": "Test product", "price_unit": 100, "tax_ids": [Command.set(taxes.ids)]})],
            })
            invoice.action_post()
            xml = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
            root = etree.fromstring(xml)
            for tax, node in zip(taxes, root.findall('.//{*}TaxTotal/{*}TaxSubtotal/{*}TaxCategory')):
                self.assertEqual(node.findtext('.//{*}ID') or False, tax.ubl_cii_tax_category_code)
                self.assertEqual(node.findtext('.//{*}TaxExemptionReasonCode') or False, tax.ubl_cii_tax_exemption_reason_code)

    @classmethod
    def invoice_and_create_line_allowance_charges(self, taxes_per_line):
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({'name': f"Test Product {idx}", 'price_unit': 100, 'tax_ids': [Command.set(taxes.ids)]})
                for idx, taxes in enumerate(taxes_per_line)
            ],
        })
        invoice.action_post()

        xml = self.env['account.edi.xml.ubl_20']._export_invoice(invoice)[0]
        root = etree.fromstring(xml)
        return root.findall('.//{*}InvoiceLine/{*}AllowanceCharge')

    def test_allowance_charge_percent_taxes(self):
        allowance_charge_nodes = self.invoice_and_create_line_allowance_charges([self.reverse_charge_tax])
        self.assertEqual(len(allowance_charge_nodes), 0)

    def test_allowance_charge_fixed_taxes(self):
        allowance_charge_nodes = self.invoice_and_create_line_allowance_charges([self.fixed_tax])

        self.assertEqual(len(allowance_charge_nodes), 1)
        self.assertEqual(allowance_charge_nodes[0].findtext('.//{*}AllowanceChargeReason'), 'Advertising')
        self.assertEqual(allowance_charge_nodes[0].findtext('.//{*}AllowanceChargeReasonCode'), 'AA')

    def test_allowance_charge_multiple_taxes(self):
        allowance_charge_nodes = self.invoice_and_create_line_allowance_charges(self.fixed_tax + self.fixed_tax2)

        self.assertEqual(len(allowance_charge_nodes), 2)
        self.assertEqual(allowance_charge_nodes[0].findtext('.//{*}AllowanceChargeReason'), 'Advertising')
        self.assertEqual(allowance_charge_nodes[0].findtext('.//{*}AllowanceChargeReasonCode'), 'AA')
        self.assertEqual(allowance_charge_nodes[1].findtext('.//{*}AllowanceChargeReason'), 'Telecommunication')
        self.assertEqual(allowance_charge_nodes[1].findtext('.//{*}AllowanceChargeReasonCode'), 'AAA')

    def test_no_allowance_charge_codes(self):
        self.fixed_tax.write({
            'ubl_cii_allowance_charge_reason': False,
            'ubl_cii_allowance_reason_code': False,
            'ubl_cii_charge_reason_code': False,
        })

        allowance_charge_nodes = self.invoice_and_create_line_allowance_charges([self.fixed_tax])
        self.assertEqual(len(allowance_charge_nodes), 0)
