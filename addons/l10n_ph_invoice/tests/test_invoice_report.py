# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from lxml import html as lxml_html

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_ph_invoice.tests.common import TestPhInvoiceCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestInvoiceReport(TestPhInvoiceCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].l10n_ph_is_vat_registered = True

        ChartTemplate = cls.env["account.chart.template"].with_company(
            cls.company_data["company"],
        )
        cls.tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")
        cls.tax_sale_0_exempt = ChartTemplate.ref("l10n_ph_tax_sale_0_exempt")
        cls.tax_sale_0_zr = ChartTemplate.ref("l10n_ph_tax_sale_0_zr")
        cls.tax_sale_3_pt010 = ChartTemplate.ref("l10n_ph_tax_sale_3_pt010")
        cls.tax_sale_10_wi011 = ChartTemplate.ref("l10n_ph_tax_sale_10_wi011")
        cls.privilege_sc_20_vat_incl = ChartTemplate.ref("l10n_ph_discount_privilege_sc_20_vat_incl")
        cls.privilege_pwd_20_vat_incl = ChartTemplate.ref("l10n_ph_discount_privilege_pwd_20_vat_incl")
        cls.privilege_sc_5 = ChartTemplate.ref("l10n_ph_discount_privilege_sc_5")

        cls.product_c = cls.env["product.product"].create({"name": "Product C", "list_price": 300.0})
        cls.product_d = cls.env["product.product"].create({"name": "Product D", "list_price": 150.0})

    def test_invoice_with_all_privileges(self):
        """
        An invoice mixing regular, SC and special discounted sales: the discount is deducted from
        the gross sales, and the sales breakdown is shown before the discount, except for the
        VATable sales on which the VAT is computed. The breakdown thus falls short of the gross
        sales by the special discount on them. Nothing is added while no privilege is applied.
        """
        invoice = self._create_invoice_with_lines(
            ("Line A (none)", self.product_a, 1000.0, {"tax_ids": self.tax_sale_12}),
            # The SC discount replaces the commercial one, as statutory discounts cannot be combined
            ("Line B (SC 20%)", self.product_b, 333.33, {"quantity": 3.0, "discount": 10.0, "tax_ids": self.tax_sale_12}),
            ("Line C (SC 5%)", self.product_c, 1000.0, {"tax_ids": self.tax_sale_12}),
            ("Line D (SC 5% zero-rated)", self.product_d, 1000.0, {"tax_ids": self.tax_sale_0_zr}),
            ("Line E (none exempt)", self.product_a, 500.0, {"tax_ids": self.tax_sale_0_exempt}),
        )
        html = self._render(invoice)
        self.assertNotIn("ID No.", html)
        self.assertNotIn("Less: Discount", html)

        self._apply_privilege(
            invoice,
            privilege_id=self.privilege_sc_20_vat_incl.id,
            apply_on="product",
            product_ids=[Command.set(self.product_b.ids)],
        )
        self._apply_privilege(
            invoice,
            privilege_id=self.privilege_sc_5.id,
            apply_on="product",
            product_ids=[Command.set((self.product_c + self.product_d).ids)],
        )
        invoice.action_post()

        html = self._render(invoice)
        self.assertEqual(self._get_totals(html), [
            ("Gross Sales", 4499.99),
            ("Less: Discount [SC/5% Senior Citizen Discount]", 300.0),
            ("Add: VAT", 234.0),
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

    def test_totals_with_special_privilege_on_tax_included_line(self):
        """ The tax-excluded discount is shown, so that the totals add up with the VAT on the discounted amount. """
        tax_incl = self.tax_sale_12.copy({"name": "12% Included", "price_include_override": "tax_included"})
        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 112.0, {"tax_ids": tax_incl}),
        )
        self._apply_privilege(invoice, privilege_id=self.privilege_sc_5.id, apply_on="all")
        invoice.action_post()

        html = self._render(invoice)
        self.assertEqual(self._get_totals(html), [
            ("Gross Sales", 100.0),
            ("Less: Discount [5% Senior Citizen Discount]", 5.0),
            ("Add: VAT", 11.4),
            ("Total Amount Due", 106.4),
        ])
        self.assertEqual(self._get_breakdown(html)["VATable Sales"], 95.0)

    def test_privilege_with_withholding_tax(self):
        """
        A fully PWD invoice is VAT-exempt: the discount is deducted from the gross sales, before the
        withholding tax computed on the discounted amount.
        """
        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 100.0, {"tax_ids": self.tax_sale_12 + self.tax_sale_10_wi011}),
        )
        self._apply_privilege(invoice, privilege_id=self.privilege_pwd_20_vat_incl.id, apply_on="all")
        invoice.action_post()

        html = self._render(invoice)
        self.assertEqual(self._get_totals(html), [
            ("Gross Sales", 100.0),
            ("Less: Discount [PWD]", 20.0),
            ("Less: Withholding Tax", 8.0),
            ("Total Amount Due", 72.0),
        ])
        self.assertIn("PWD ID No.:", html)

    def test_non_vat_seller_with_privilege(self):
        """ A non-VAT seller's sales breakdown is shown before the discount, as its gross sales. """
        self.company_data["company"].l10n_ph_is_vat_registered = False
        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 100.0, {"tax_ids": self.tax_sale_0_exempt}),
            ("Line B", self.product_b, 100.0, {"tax_ids": self.tax_sale_3_pt010}),
        )
        self._apply_privilege(invoice, privilege_id=self.privilege_sc_5.id, apply_on="all")
        invoice.action_post()

        html = self._render(invoice)
        self.assertEqual(self._get_totals(html), [
            ("Gross Sales", 200.0),
            ("Less: Discount [5% Senior Citizen Discount]", 10.0),
            ("Total Amount Due", 190.0),
        ])
        self.assertEqual(self._get_breakdown(html), {
            "Exempt Sales": 100.0,
            "Sales Subject to Percentage Tax": 100.0,
        })

    # ============================================================
    #  Helpers
    # ============================================================

    def _get_rows(self, html, xpath):
        """ Return the (label, amount) pairs of the two-cell rows matching ``xpath``. """
        return [
            (" ".join(row[0].text_content().split()), float(re.sub(r"[^\d.-]", "", row[1].text_content())))
            for row in lxml_html.fromstring(html).xpath(xpath)
        ]

    def _get_totals(self, html):
        """ Return the (label, amount) rows of the totals table, in order. """
        return self._get_rows(html, "//table[contains(@class, 'o_total_table')]//tr")

    def _get_breakdown(self, html):
        """ Return the amounts of the sales breakdown box, by label. """
        return dict(self._get_rows(html, "//div[@id='total']/ancestor::div[hasclass('col-5')]/preceding-sibling::div//tr"))
