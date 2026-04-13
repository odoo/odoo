# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_edi_ubl_cii_tax_extension.models.account_edi_common import FIX_WRONG_CODES_MAPPING
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiUblCiiTaxExtension(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template'):
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
                reason_code = tax.ubl_cii_tax_exemption_reason_code
                reason_code = FIX_WRONG_CODES_MAPPING.get(reason_code, reason_code)
                self.assertEqual(node.findtext('.//{*}ID') or False, tax.ubl_cii_tax_category_code)
                self.assertEqual(node.findtext('.//{*}TaxExemptionReasonCode') or False, reason_code)

    def test_reverse_charge_tax_with_discount_ubl_20(self):
        self.reverse_charge_tax.amount = 0
        self.company_data['company'].early_pay_discount_computation = 'mixed'
        epd_payment_term = self.env['account.payment.term'].create({
            'name': '2% discount if paid within 7 days',
            'company_id': self.company_data['company'].id,
            'line_ids': [Command.create({
                'value': 'balance',
                'days': 0,
                'discount_percentage': 2,
                'discount_days': 7
            })]
        })
        invoice = self.env["account.move"].create({
            "partner_id": self.partner_a.id,
            "move_type": "out_invoice",
            "invoice_payment_term_id": epd_payment_term.id,
            "invoice_line_ids": [
                Command.create({"name": "Test product", "price_unit": 100, "tax_ids": [Command.set(self.reverse_charge_tax.ids)]})],
        })
        invoice.action_post()
        xml = self.env['account.edi.xml.ubl_20']._export_invoice(invoice)[0]
        root = etree.fromstring(xml)

        subtotals = root.findall('.//{*}TaxTotal/{*}TaxSubtotal/{*}TaxCategory')
        self.assertEqual(len(subtotals), 2, "Expected for the Tax and the EPD")
        reverse_charge, discount = subtotals

        self.assertEqual(reverse_charge.findtext('.//{*}ID'), 'AE')
        self.assertEqual(reverse_charge.findtext('.//{*}TaxExemptionReasonCode'), 'VATEX-EU-AE')
        self.assertEqual(reverse_charge.findtext('.//{*}TaxableAmount'), '98.00')

        self.assertEqual(discount.findtext('.//{*}ID'), 'AE')
        self.assertEqual(discount.findtext('.//{*}TaxableAmount'), '2.00')
        self.assertEqual(discount.findtext('.//{*}TaxAmount'), '0.00')
