# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiUblCiiTaxExtension(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.reverse_charge_tax = cls.company_data['default_tax_sale'].copy({'ubl_cii_tax_category_code': 'AE', 'ubl_cii_tax_exemption_reason_code': 'VATEX_EU_AE'})
        cls.zero_rated_tax = cls.company_data['default_tax_sale'].copy({'ubl_cii_tax_category_code': 'Z'})
        cls.prod_tax = cls.company_data['default_tax_sale'].copy({'ubl_cii_tax_category_code': 'M'})
        cls.free_export_tax = cls.company_data['default_tax_sale'].copy({'ubl_cii_tax_category_code': 'G', 'ubl_cii_tax_exemption_reason_code': 'VATEX-EU-132-1G'})

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
