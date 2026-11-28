from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestMadagascarInvoiceReport(AccountTestInvoicingCommon):
    """CPF art. IV-21: an invoice shows the NIF and the STAT of the seller and the customer, and its total in words."""

    @classmethod
    @AccountTestInvoicingCommon.setup_country("mg")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.partner_id.write(
            {
                "vat": "4001234567",
                "additional_identifiers": {
                    "MG_NIF": "4001234567",
                    "MG_STAT": "46101112010000123",
                },
            },
        )
        cls.mg = cls.env.ref("base.mg")
        cls.partner_a.write(
            {
                "country_id": cls.mg.id,
                "vat": "4000654321",
                "additional_identifiers": {
                    "MG_NIF": "4000654321",
                    "MG_STAT": "46521112012000222",
                },
            },
        )

    def _render_invoice(self, invoice) -> str:
        return (
            self.env["ir.actions.report"]
            ._render_qweb_html("account.report_invoice", invoice.ids)[0]
            .decode()
        )

    def test_company_settings(self):
        self.assertTrue(self.company.display_invoice_amount_total_words)
        self.assertEqual(self.mg.vat_label, "NIF")

    def test_customer_identifiers(self):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner_a,
            amounts=[1000],
            post=True,
        )
        self.assertEqual(
            invoice._get_document_partner_ident_line(),
            "NIF: 4000654321<br/>STAT: 46521112012000222",
        )

        # The NIF may only be in its identifier, without Tax ID
        self.partner_a.vat = False
        self.assertEqual(
            invoice._get_document_partner_ident_line(),
            "NIF: 4000654321<br/>STAT: 46521112012000222",
        )

        # A customer without identifiers gets no line
        self.partner_a.additional_identifiers = {}
        self.assertEqual(invoice._get_document_partner_ident_line(), "")

    def test_foreign_customer_identifiers(self):
        """A foreign customer has neither NIF nor STAT: keep the generic Tax ID line."""
        partner_fr = self.env["res.partner"].create(
            {
                "name": "Client Paris",
                "country_id": self.env.ref("base.fr").id,
                "vat": "FR23334175221",
            },
        )
        invoice = self.init_invoice(
            "out_invoice",
            partner=partner_fr,
            amounts=[1000],
            post=True,
        )
        self.assertEqual(
            invoice._get_document_partner_ident_line(),
            "NIF: FR23334175221",
        )

    def test_invoice_report(self):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner_a,
            amounts=[150000],
            taxes=self.env["account.chart.template"].ref("mg_tax_sale_20"),
            post=True,
        )
        html = self._render_invoice(invoice)
        for expected in (
            # Company
            "NIF</span>:",
            "4001234567",
            "STAT: <span>46101112010000123</span>",
            # Customer
            "NIF: 4000654321<br/>STAT: 46521112012000222",
            # Total in figures and in words
            "180,000.00",
            invoice.amount_total_words,
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)
        self.assertIn("Eighty Thousand", invoice.amount_total_words)
