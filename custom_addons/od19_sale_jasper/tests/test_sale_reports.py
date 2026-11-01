# -*- coding: utf-8 -*-
"""Tests for the seven Sales Jasper forms/reports ported from Odoo 15.

Every legacy ``dtr_sales_form`` / ``dtr_sales_report`` template shares the same
wizard engine (:class:`od19.jasper.report`); the tests below check, per form,
that the shipped ``.jasper`` exists, that the parameters match the legacy
contract read by the ported ``queryString`` and that the wizard view is the
default form view of its model.
"""
import os
from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class SaleReportTestBase:
    """Shared fixtures and assertions.

    Kept as a plain mixin (not a :class:`TransactionCase`) so the test runner
    does not collect it as an abstract, model-less test case.  Odoo's test
    loader only reads ``test_case_class.__dict__`` unless
    ``allow_inherited_tests_method`` is set, hence the flag below so every
    concrete form runs the shared contract tests.
    """

    allow_inherited_tests_method = True
    model = None
    default_file = None
    view_xmlid = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Sale Report Partner", "is_company": True}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Sale Report Product", "list_price": 100.0}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        cls.order.action_confirm()

    def default_ids(self):
        return self.order.ids

    def _report(self, ids=None, **values):
        report = self.env[self.model].create(values)
        if ids is None:
            ids = self.default_ids()
        if ids is not False:
            report = report.with_context(active_ids=ids)
        return report

    # ------------------------------------------------------------- shipping
    def test_default_jasper_file_is_shipped(self):
        report = self.env[self.model].create({})
        self.assertTrue(report.jasper_file.endswith(self.default_file))
        self.assertTrue(os.path.isfile(report.jasper_file), report.jasper_file)

    # ---------------------------------------------------- parameter contract
    def test_language_flows_to_parameters(self):
        report = self._report(p_language="english")
        self.assertEqual(report.get_parameters()["p_language"], "english")

    def test_locale_follows_date_type(self):
        report = self._report(date_type="BE")
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    # ---------------------------------------------------------------- views
    def test_wizard_view_is_the_default_form_view(self):
        view = self.env[self.model].get_views([[False, "form"]])["views"]["form"]
        self.assertEqual(view["id"], self.env.ref(self.view_xmlid).id)
        self.assertIn('filename="name_pdf"', view["arch"])
        self.assertIn('filename="name_xlsx"', view["arch"])


class TestSaleQuotationForm(SaleReportTestBase, TransactionCase):
    """F-S-003 Quotation Form."""

    model = "sale.quotation.form"
    default_file = "sale_quotation_form.jasper"
    view_xmlid = "od19_sale_jasper.view_sale_quotation_form"

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Where"], "WHERE so.id in (%s)" % self.order.id)
        self.assertEqual(parameters["p_Company_No"], str(self.order.company_id.id))
        self.assertEqual(parameters["p_ISO"], "")
        self.assertTrue(parameters["p_Path"].endswith("/"))
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(report.name, self.order.display_name)

    def test_signature_toggles_flow_to_parameters(self):
        report = self._report(p_EName=False, p_ESignature=False)
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_EName"], "False")
        self.assertEqual(parameters["p_ESignature"], "False")

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(ids=[]).get_parameters()

    def test_partner_ids_for_send_by_email(self):
        self.assertEqual(
            self._report().get_partner_ids_for_send_by_email(), self.partner
        )


class TestSaleOrderProformaForm(SaleReportTestBase, TransactionCase):
    """F-S-004 Proforma Invoice Form."""

    model = "sale.order.proforma.form"
    default_file = "sale_order_proforma_form.jasper"
    view_xmlid = "od19_sale_jasper.view_sale_order_proforma_form"

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Where"], "WHERE so.id in (%s)" % self.order.id)
        self.assertEqual(parameters["p_Company_No"], str(self.order.company_id.id))
        self.assertEqual(parameters["p_ISO"], "")
        self.assertTrue(parameters["p_Path"].endswith("/"))
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertEqual(report.name, self.order.display_name)

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(ids=[]).get_parameters()

    def test_partner_ids_for_send_by_email(self):
        self.assertEqual(
            self._report().get_partner_ids_for_send_by_email(), self.partner
        )


class TestWarrantyCardForm(SaleReportTestBase, TransactionCase):
    """Warranty Card Form, re-targeted from dtr_warranty_card to a claim."""

    model = "warranty.card.form"
    default_file = "warranty_card_form.jasper"
    view_xmlid = "od19_sale_jasper.view_warranty_card_form"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.claim = cls.env["od19.warranty.claim"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "description": "Warranty card test claim",
            }
        )

    def default_ids(self):
        return self.claim.ids

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Where"], " where claim.id in (%s) " % self.claim.id
        )
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(report.name, self.claim.display_name)

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(ids=[]).get_parameters()

    def test_partner_ids_for_send_by_email(self):
        self.assertEqual(
            self._report().get_partner_ids_for_send_by_email(), self.partner
        )


class TestSaleOrderOutstandingReport(SaleReportTestBase, TransactionCase):
    """R-S-001 Sale Order Outstanding Report."""

    model = "sale.order.outstanding.report"
    default_file = "sale_order_outstanding_report.jasper"
    view_xmlid = "od19_sale_jasper.view_sale_order_outstanding_report"

    def test_condition_uses_selected_orders(self):
        report = self._report()
        self.assertEqual(
            report.get_parameters()["p_Condition"],
            " where a.id in (%s)" % self.order.id,
        )

    def test_condition_falls_back_to_company(self):
        report = self._report(ids=[])
        condition = report.get_parameters()["p_Condition"]
        self.assertIn("a.company_id = %s" % self.env.company.id, condition)
        self.assertIn("a.state in ('sale','done')", condition)

    def test_show_picture_toggles_to_parameters(self):
        report = self._report(p_Show_Picture=False)
        self.assertEqual(report.get_parameters()["p_Show_Picture"], "False")

    def test_parameters_expose_signer_and_path(self):
        parameters = self._report().get_parameters()
        self.assertEqual(parameters["p_User_ID"], str(self.env.user.id))
        self.assertTrue(parameters["p_Path"].endswith("/"))
        self.assertEqual(parameters["p_ISO"], "")


class TestSaleOrderValuesReport(SaleReportTestBase, TransactionCase):
    """R-S-002 Sale Order Values Report."""

    model = "sale.order.values.report"
    default_file = "sale_order_values_report.jasper"
    view_xmlid = "od19_sale_jasper.view_sale_order_values_report"

    def test_period_and_grouping_flow_to_parameters(self):
        report = self._report(
            date_start=date(2025, 1, 1),
            date_end=date(2025, 1, 31),
            p_Group="2",
            p_Group_Name="Product Category",
        )
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Start_Date"], "2025-01-01")
        self.assertEqual(parameters["p_To_Date"], "2025-01-31")
        self.assertEqual(parameters["p_Group"], "2")
        self.assertEqual(parameters["p_Group_Name"], "Product Category")
        self.assertEqual(parameters["p_User_ID"], str(self.env.user.id))

    def test_brand_grouping_is_no_longer_offered(self):
        field = self.env["sale.order.values.report"]._fields["p_Group"]
        self.assertNotIn("3", [key for key, _label in field.selection])

    def test_signature_toggles_flow_to_parameters(self):
        report = self._report(p_EName=False, p_ESignature=False)
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_EName"], "False")
        self.assertEqual(parameters["p_ESignature"], "False")


class TestSaleInvoiceValuesReport(TestSaleOrderValuesReport):
    """R-S-003 Sale Invoice Values Report (same contract, own template)."""

    model = "sale.invoice.values.report"
    default_file = "sale_invoice_values_report.jasper"
    view_xmlid = "od19_sale_jasper.view_sale_invoice_values_report"


class TestFirstSalesIncomingReport(SaleReportTestBase, TransactionCase):
    """R-S-004 First Sales Incoming Report."""

    model = "first.sales.incoming.report"
    default_file = "first_sales_incoming_report.jasper"
    view_xmlid = "od19_sale_jasper.view_first_sales_incoming_report"

    def test_year_and_month_flow_to_parameters(self):
        report = self._report(p_Year=2025, p_Month=6)
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Year"], "2025")
        self.assertEqual(parameters["p_Month"], "6")
        self.assertEqual(parameters["p_User_ID"], str(self.env.user.id))

    def test_default_period_is_the_current_month(self):
        report = self.env["first.sales.incoming.report"].create({})
        today = date.today()
        self.assertEqual(report.p_Year, today.year)
        self.assertEqual(report.p_Month, today.month)
