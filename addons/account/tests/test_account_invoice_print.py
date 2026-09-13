from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountInvoicePrint(AccountTestInvoicingCommon):
    def _render_invoices(self, invoices):
        report_class = self.registry["ir.actions.report"]
        original = report_class._render_qweb_html
        rendered = []

        def spy(report_model, report_ref, docids, data=None):
            report = report_model._get_report(report_ref)
            rendered.append((report.report_name, list(docids or [])))
            return original(report_model, report_ref, docids, data=data)

        with patch.object(report_class, "_render_qweb_html", spy):
            content, report_type = (
                self.env["ir.actions.report"]
                .with_context(force_report_rendering=True)
                ._render_qweb_pdf("account.account_invoices", invoices.ids)
            )
        return content, report_type, rendered

    def test_the_invoice_report_prints_each_invoice_with_its_default_template(self):
        default_invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, products=self.product_a, post=True
        )
        partner_invoice = self.init_invoice(
            "out_invoice", partner=self.partner_b, products=self.product_a, post=True
        )
        self.partner_b.invoice_template_pdf_report_id = self.env.ref(
            "account.account_invoices_without_payment"
        )

        content, report_type, rendered = self._render_invoices(
            default_invoice | partner_invoice
        )

        self.assertEqual(report_type, "pdf")
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertEqual(
            rendered,
            [
                ("account.report_invoice_with_payments", default_invoice.ids),
                ("account.report_invoice", partner_invoice.ids),
            ],
        )

    def test_invoices_without_a_default_template_render_in_one_pass(self):
        invoices = self.init_invoice(
            "out_invoice", partner=self.partner_a, products=self.product_a, post=True
        ) | self.init_invoice(
            "out_invoice", partner=self.partner_a, products=self.product_a, post=True
        )

        _content, _report_type, rendered = self._render_invoices(invoices)

        self.assertEqual(
            rendered, [("account.report_invoice_with_payments", invoices.ids)]
        )
