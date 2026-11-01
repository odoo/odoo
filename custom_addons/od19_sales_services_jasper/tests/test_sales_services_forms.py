# -*- coding: utf-8 -*-
"""Tests for the seven Sales Services Jasper forms/reports ported from Odoo 15.

Every legacy ``dtr_sales_services_form`` / ``dtr_sales_services_report``
template shares the same wizard engine (:class:`od19.jasper.report`); the tests
below check, per form, that the shipped ``.jasper`` exists, that the parameters
match the legacy contract read by the ported ``queryString`` and that the wizard
view is the default form view of its model.
"""
import os
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class SalesServicesReportTestBase:
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
            {"name": "Sales Services Partner", "is_company": True}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Sales Services Product", "list_price": 100.0}
        )

    def default_ids(self):
        return self.doc.ids

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
        self.assertTrue(
            report.jasper_file.endswith(self.default_file), report.jasper_file
        )
        self.assertTrue(os.path.isfile(report.jasper_file), report.jasper_file)

    # ---------------------------------------------------------------- locale
    def test_locale_follows_date_type(self):
        report = self._report(date_type="BE")
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_locale_is_en_for_ad(self):
        report = self._report(date_type="AD")
        self.assertEqual(report.get_parameters()["p_locale"], "en")

    # ---------------------------------------------------------------- views
    def test_wizard_view_is_the_default_form_view(self):
        view = self.env[self.model].get_views([[False, "form"]])["views"]["form"]
        self.assertEqual(view["id"], self.env.ref(self.view_xmlid).id)
        self.assertIn('filename="name_pdf"', view["arch"])


class TestSalesServicesForm(SalesServicesReportTestBase, TransactionCase):
    """F-SS-001 Sales Services Form (service card)."""

    model = "sales.services.form"
    default_file = "sales_services_form.jasper"
    view_xmlid = "od19_sales_services_jasper.view_sales_services_form"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc = cls.env["od19.service.card"].create(
            {"partner_id": cls.partner.id, "product_id": cls.product.id}
        )

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Where"], "WHERE ss.id in (%s)" % self.doc.id)
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(report.name, self.doc.display_name)

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(ids=[]).get_parameters()

    def test_partner_ids_for_send_by_email(self):
        self.assertEqual(
            self._report().get_partner_ids_for_send_by_email(), self.partner
        )


class TestClaimForm(SalesServicesReportTestBase, TransactionCase):
    """F-SS-002 Claim Form (warranty claim)."""

    model = "claim.form"
    default_file = "claim_form.jasper"
    view_xmlid = "od19_sales_services_jasper.view_claim_form"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc = cls.env["od19.warranty.claim"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "description": "Claim form test",
            }
        )

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Where"], "WHERE claim.id in (%s)" % self.doc.id
        )
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(report.name, self.doc.display_name)

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(ids=[]).get_parameters()

    def test_partner_ids_for_send_by_email(self):
        self.assertEqual(
            self._report().get_partner_ids_for_send_by_email(), self.partner
        )


class TestProductReturnForm(SalesServicesReportTestBase, TransactionCase):
    """F-SS-003 Product Return Form."""

    model = "product.return.form"
    default_file = "product_return_form.jasper"
    view_xmlid = "od19_sales_services_jasper.view_product_return_form"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc = cls.env["od19.product.return"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "reason": "other",
            }
        )

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Where"], "WHERE pr.id in (%s)" % self.doc.id)
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(report.name, self.doc.display_name)

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(ids=[]).get_parameters()

    def test_partner_ids_for_send_by_email(self):
        self.assertEqual(
            self._report().get_partner_ids_for_send_by_email(), self.partner
        )


class TestDistributeOrderForm(SalesServicesReportTestBase, TransactionCase):
    """F-IV-013 Distribute Order Form (transport order)."""

    model = "distribute.order.form"
    default_file = "distribute_order_form.jasper"
    view_xmlid = "od19_sales_services_jasper.view_distribute_order_form"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc = cls.env["od19.transport.order"].create(
            {
                "origin_location": "Bangkok",
                "destination_location": "Chiang Mai",
            }
        )

    def test_parameters_use_raw_ids_key(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(parameters["ids"], "where dto.id in (%s)" % self.doc.id)
        self.assertNotIn("p_Where", parameters)
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(report.name, self.doc.display_name)

    def test_show_report_rejects_unready_document(self):
        # A freshly created transport order is in ``draft``, which the legacy
        # report rejected.
        report = self._report()
        with self.assertRaises(ValidationError):
            report.show_report()


class TestSalesServicesReport(SalesServicesReportTestBase, TransactionCase):
    """R-SS-001 Sales Services Report (period report)."""

    model = "sales.services.report"
    default_file = "sales_services_report.jasper"
    view_xmlid = "od19_sales_services_jasper.view_sales_services_report"

    def default_ids(self):
        return []

    def test_period_parameters_follow_legacy_contract(self):
        report = self._report(
            p_Start_Date=date(2025, 1, 1), p_End_Date=date(2025, 1, 31)
        )
        parameters = report.get_parameters()
        self.assertIn(
            "WHERE ss.state not in ('draft','cancelled')", parameters["p_Where"]
        )
        self.assertIn("date(ss.service_date) >= '2025-01-01'", parameters["p_Where"])
        self.assertIn("date(ss.service_date) <= '2025-01-31'", parameters["p_Where"])
        self.assertIn(
            "ss.company_id = %s" % self.env.company.id, parameters["p_Where"]
        )
        self.assertEqual(parameters["p_Start_Date"], "2025-01-01")
        self.assertEqual(parameters["p_End_Date"], "2025-01-31")
        self.assertEqual(parameters["p_Customer"], "ทั้งหมด")
        self.assertEqual(parameters["p_Print_By"], self.env.user.name)
        self.assertEqual(report.name, "Sales Services Report")

    def test_customer_filter_flows_to_parameters(self):
        report = self._report(
            p_Start_Date=date(2025, 1, 1),
            p_End_Date=date(2025, 1, 31),
            p_Customer=[(6, 0, self.partner.ids)],
        )
        parameters = report.get_parameters()
        self.assertIn(
            "ss.partner_id in (%s)" % self.partner.id, parameters["p_Where"]
        )
        self.assertEqual(parameters["p_Customer"], self.partner.display_name)


class TestClaimReport(SalesServicesReportTestBase, TransactionCase):
    """R-SS-002 Claim Report (period report)."""

    model = "claim.report"
    default_file = "claim_report.jasper"
    view_xmlid = "od19_sales_services_jasper.view_claim_report"

    def default_ids(self):
        return []

    def test_period_parameters_follow_legacy_contract(self):
        report = self._report(
            p_Start_Date=date(2025, 1, 1), p_End_Date=date(2025, 1, 31)
        )
        parameters = report.get_parameters()
        self.assertIn("WHERE claim.state not in ('draft')", parameters["p_Where"])
        self.assertIn(
            "date(claim.claim_date) >= '2025-01-01'", parameters["p_Where"]
        )
        self.assertIn(
            "date(claim.claim_date) <= '2025-01-31'", parameters["p_Where"]
        )
        self.assertIn(
            "claim.company_id = %s" % self.env.company.id, parameters["p_Where"]
        )
        self.assertEqual(parameters["p_Customer"], "ทั้งหมด")
        self.assertEqual(report.name, "Claim Report")

    def test_customer_filter_flows_to_parameters(self):
        report = self._report(
            p_Start_Date=date(2025, 1, 1),
            p_End_Date=date(2025, 1, 31),
            p_Customer=[(6, 0, self.partner.ids)],
        )
        parameters = report.get_parameters()
        self.assertIn(
            "claim.partner_id in (%s)" % self.partner.id, parameters["p_Where"]
        )


class TestProductReturnReport(SalesServicesReportTestBase, TransactionCase):
    """R-SS-003 Product Return Report (period report)."""

    model = "product.return.report"
    default_file = "product_return_report.jasper"
    view_xmlid = "od19_sales_services_jasper.view_product_return_report"

    def default_ids(self):
        return []

    def test_period_parameters_follow_legacy_contract(self):
        report = self._report(
            p_Start_Date=date(2025, 1, 1), p_End_Date=date(2025, 1, 31)
        )
        parameters = report.get_parameters()
        self.assertIn("WHERE pr.state not in ('draft')", parameters["p_Where"])
        self.assertIn(
            "date(pr.return_date) >= '2025-01-01'", parameters["p_Where"]
        )
        self.assertIn(
            "date(pr.return_date) <= '2025-01-31'", parameters["p_Where"]
        )
        self.assertIn(
            "pr.company_id = %s" % self.env.company.id, parameters["p_Where"]
        )
        self.assertEqual(parameters["p_Customer"], "ทั้งหมด")
        self.assertEqual(report.name, "Product Return Report")

    def test_customer_filter_flows_to_parameters(self):
        report = self._report(
            p_Start_Date=date(2025, 1, 1),
            p_End_Date=date(2025, 1, 31),
            p_Customer=[(6, 0, self.partner.ids)],
        )
        parameters = report.get_parameters()
        self.assertIn(
            "pr.partner_id in (%s)" % self.partner.id, parameters["p_Where"]
        )
