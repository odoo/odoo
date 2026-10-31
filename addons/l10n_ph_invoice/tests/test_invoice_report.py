# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from lxml import html as lxml_html

from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestInvoiceReport(TestPhCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].l10n_ph_is_vat_registered = True
        chart_template = cls.env["account.chart.template"].with_company(cls.company_data["company"])
        cls.tax_vatable = chart_template.ref("l10n_ph_tax_sale_12")
        cls.tax_vat_exempt = chart_template.ref("l10n_ph_tax_sale_0_exempt")
        cls.tax_zero_rated = chart_template.ref("l10n_ph_tax_sale_0_zr")
        cls.tax_percentage = chart_template.ref("l10n_ph_tax_sale_3_pt010")
        cls.tax_withholding = chart_template.ref("l10n_ph_tax_sale_10_wi011")
        cls.privilege_sc = chart_template.ref("l10n_ph_discount_privilege_sc_20_vat_incl")
        cls.privilege_pwd = chart_template.ref("l10n_ph_discount_privilege_pwd_20_vat_incl")
        cls.privilege_special = chart_template.ref("l10n_ph_discount_privilege_sc_5")

    def _create_privileged_invoice(self, *lines):
        """
        Create and post an invoice, after applying the privileges of its lines.

        :param lines: the values of each invoice line; its ``privilege`` key holds
            the privilege to apply to the line, if any
        """
        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    **{key: value for key, value in line.items() if key != "privilege"},
                )
                for line in lines
            ],
        )
        line_privileges = list(zip(invoice.invoice_line_ids, [line.get("privilege") for line in lines]))
        for privilege in dict.fromkeys(privilege for _line, privilege in line_privileges if privilege):
            wizard = self.env["l10n_ph.discount.privilege.wizard"].create({
                "move_id": invoice.id,
                "privilege_id": privilege.id,
            })
            wizard.line_ids = wizard.line_ids.filtered(lambda wizard_line: (wizard_line.invoice_line_id, privilege) in line_privileges)
            wizard.action_confirm()
        invoice.action_post()
        return invoice

    def _render(self, invoice, report="account.report_invoice"):
        html, _ = self.env["ir.actions.report"]._render_qweb_html(report, invoice.ids)
        return html.decode()

    def _parse_amount(self, text):
        return float(re.sub(r"[^\d.-]", "", text))

    def _get_rows(self, html, xpath):
        return [
            (" ".join(row[0].text_content().split()), self._parse_amount(row[1].text_content()))
            for row in lxml_html.fromstring(html).xpath(xpath)
        ]

    def _get_totals(self, html):
        """ Return the (label, amount) rows of the totals table, in order. """
        return self._get_rows(html, "//table[contains(@class, 'o_total_table')]//tr")

    def _get_breakdown(self, html):
        """ Return the amounts of the sales breakdown box, by label. """
        return dict(self._get_rows(html, "//div[@id='total']/ancestor::div[hasclass('col-5')]/preceding-sibling::div//tr"))

    def test_invoice_without_privilege(self):
        invoice = self._create_privileged_invoice({"price_unit": 100.0, "tax_ids": self.tax_vatable})
        html = self._render(invoice)
        self.assertNotIn("ID No.", html)
        self.assertNotIn("Less: Discount", html)

    def test_invoice_with_all_privileges(self):
        """
        An invoice mixing regular, SC and special discounted sales: the discount is deducted from
        the amount net of VAT, and the sales breakdown is shown before the discount, except for the
        VATable sales on which the VAT is computed. The breakdown thus falls short of the amount
        net of VAT by the special discount on them.
        """
        invoice = self._create_privileged_invoice(
            {"price_unit": 1000.0, "tax_ids": self.tax_vatable},
            # The SC discount replaces the commercial one, as statutory discounts cannot be combined
            {"quantity": 3.0, "price_unit": 333.33, "discount": 10.0, "tax_ids": self.tax_vatable, "privilege": self.privilege_sc},
            {"price_unit": 1000.0, "tax_ids": self.tax_vatable, "privilege": self.privilege_special},
            {"price_unit": 1000.0, "tax_ids": self.tax_zero_rated, "privilege": self.privilege_special},
            {"price_unit": 500.0, "tax_ids": self.tax_vat_exempt},
        )
        self.assertRecordValues(invoice, [{"amount_untaxed": 4199.99, "amount_tax": 234.0, "amount_total": 4433.99}])
        html = self._render(invoice)
        self.assertEqual(self._get_totals(html), [
            ("Amount: Net of VAT", 4499.99),
            ("Less: Discount [SC/5% Senior Citizen Discount]", 300.0),
            ("Add: VAT", 234.0),
            ("Total Sales (VAT-Inclusive)", 4433.99),
            ("Total Amount Due", 4433.99),
        ])
        self.assertEqual(self._get_breakdown(html), {
            "VATable Sales": 1950.0,
            "VAT": 234.0,
            "Zero-Rated Sales": 1000.0,
            "VAT-Exempt Sales": 1499.99,
        })
        self.assertIn("SC/5% Senior Citizen Discount ID No.:", html)
        self.assertIn("SC/5% Senior Citizen Discount Signature:", html)

    def test_special_privilege_on_tax_included_line(self):
        """ The tax-excluded discount is shown, so that the totals add up with the VAT on the discounted amount. """
        tax_included = self.tax_vatable.copy({"name": "12% Included", "price_include_override": "tax_included"})
        invoice = self._create_privileged_invoice(
            {"price_unit": 112.0, "tax_ids": tax_included, "privilege": self.privilege_special},
        )
        self.assertRecordValues(invoice, [{"amount_untaxed": 95.0, "amount_tax": 11.4, "amount_total": 106.4}])
        html = self._render(invoice)
        self.assertEqual(self._get_totals(html), [
            ("Amount: Net of VAT", 100.0),
            ("Less: Discount [5% Senior Citizen Discount]", 5.0),
            ("Add: VAT", 11.4),
            ("Total Sales (VAT-Inclusive)", 106.4),
            ("Total Amount Due", 106.4),
        ])
        self.assertEqual(self._get_breakdown(html)["VATable Sales"], 95.0)

    def test_privilege_with_withholding_tax(self):
        """
        A fully PWD invoice is VAT-exempt: the discount is deducted from the total sales, before the
        withholding tax computed on the discounted amount.
        """
        invoice = self._create_privileged_invoice(
            {"price_unit": 100.0, "tax_ids": self.tax_vatable + self.tax_withholding, "privilege": self.privilege_pwd},
        )
        html = self._render(invoice)
        self.assertEqual(self._get_totals(html), [
            ("Total Sales", 100.0),
            ("Less: Discount [PWD]", 20.0),
            ("Less: Withholding Tax", 8.0),
            ("Total Amount Due", 72.0),
        ])
        self.assertIn("PWD ID No.:", html)

    def test_non_vat_seller_with_privilege(self):
        """ A non-VAT seller's sales breakdown is shown before the discount, as its total sales. """
        self.company_data["company"].l10n_ph_is_vat_registered = False
        invoice = self._create_privileged_invoice(
            {"price_unit": 100.0, "tax_ids": self.tax_vat_exempt, "privilege": self.privilege_special},
            {"price_unit": 100.0, "tax_ids": self.tax_percentage, "privilege": self.privilege_special},
        )
        html = self._render(invoice)
        self.assertEqual(self._get_totals(html), [
            ("Total Sales", 200.0),
            ("Less: Discount [5% Senior Citizen Discount]", 10.0),
            ("Total Amount Due", 190.0),
        ])
        self.assertEqual(self._get_breakdown(html), {
            "Exempt Sales": 100.0,
            "Sales Subject to Percentage Tax": 100.0,
        })
