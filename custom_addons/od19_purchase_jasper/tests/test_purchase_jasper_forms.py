import os

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRequestsForQuotationForm(TransactionCase):
    """F-P-002 Requests for Quotation (ใบขอราคา)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "RFQ Vendor", "is_company": True}
        )
        cls.order = cls.env["purchase.order"].create(
            {"partner_id": cls.partner.id}
        )

    def _report(self, order=True, **values):
        report = self.env["requests.for.quotation.form"].create(values)
        if order:
            report = report.with_context(active_ids=self.order.ids)
        return report

    def test_default_jasper_file_points_to_requests_for_quotation_report(self):
        report = self.env["requests.for.quotation.form"].create({})
        self.assertTrue(
            report.jasper_file.endswith("requests_for_quotation_report.jasper")
        )
        self.assertTrue(
            os.path.isfile(report.get_jrxml_file()), report.get_jrxml_file()
        )

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Where"], "where po.id in (%s)" % self.order.id
        )
        self.assertEqual(parameters["p_ISO"], "")
        self.assertTrue(parameters["p_Path"].endswith("/"))
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(parameters["p_Where"].startswith("where "), True)
        self.assertEqual(report.name, self.order.display_name)

    def test_locale_follows_date_type(self):
        report = self._report(date_type="BE")
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(order=False).get_parameters()

    def test_partner_ids_for_send_by_email(self):
        report = self._report()
        self.assertEqual(report.get_partner_ids_for_send_by_email(), self.partner)

    def test_wizard_view_is_the_default_form_view(self):
        view = self.env["requests.for.quotation.form"].get_views(
            [[False, "form"]]
        )["views"]["form"]
        self.assertEqual(
            view["id"],
            self.env.ref(
                "od19_purchase_jasper.view_requests_for_quotation_form"
            ).id,
        )


@tagged("post_install", "-at_install")
class TestPoPurchaseRequestForm(TransactionCase):
    """F-P-001 Purchase Order referencing a Purchase Request."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        vals = {}
        picking_type = cls.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        if picking_type:
            vals["picking_type_id"] = picking_type.id
        cls.request = cls.env["purchase.request"].create(vals)

    def _report(self, request=True, **values):
        report = self.env["po.purchase.request.form"].create(values)
        if request:
            report = report.with_context(active_ids=self.request.ids)
        return report

    def test_default_jasper_file_points_to_po_purchase_request_report(self):
        report = self.env["po.purchase.request.form"].create({})
        self.assertTrue(
            report.jasper_file.endswith("po_purchase_request_report.jasper")
        )
        self.assertTrue(
            os.path.isfile(report.get_jrxml_file()), report.get_jrxml_file()
        )

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_PRNo"], "WHERE p.id in (%s)" % self.request.id
        )
        self.assertEqual(parameters["p_ISO"], "")
        self.assertTrue(parameters["p_Path"].endswith("/"))
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(report.name, self.request.display_name)

    def test_locale_follows_date_type(self):
        report = self._report(date_type="BE")
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(request=False).get_parameters()

    def test_show_report_rejects_unapproved_request(self):
        report = self._report()
        self.assertEqual(self.request.state, "draft")
        with self.assertRaises(ValidationError):
            report.show_report()

    def test_wizard_view_is_the_default_form_view(self):
        view = self.env["po.purchase.request.form"].get_views(
            [[False, "form"]]
        )["views"]["form"]
        self.assertEqual(
            view["id"],
            self.env.ref("od19_purchase_jasper.view_po_purchase_request_form").id,
        )


@tagged("post_install", "-at_install")
class TestPurchaseOrderPeriodReport(TransactionCase):
    """r_p_001 Purchase Order By Period - not bound to a document."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Period Vendor", "is_company": True, "supplier_rank": 1}
        )

    def test_default_jasper_file_points_to_purchase_order_period_report(self):
        report = self.env["purchase.order.period.report"].create({})
        self.assertTrue(
            report.jasper_file.endswith("purchase_order_period_report.jasper")
        )
        self.assertTrue(
            os.path.isfile(report.get_jrxml_file()), report.get_jrxml_file()
        )

    def test_default_start_date_is_the_first_day_of_the_month(self):
        report = self.env["purchase.order.period.report"].create({})
        self.assertEqual(report.startdate.day, 1)
        self.assertEqual(report.startdate, report._default_start_date())

    def test_parameters_follow_legacy_contract(self):
        report = self.env["purchase.order.period.report"].create(
            {"partner": [(6, 0, self.vendor.ids)]}
        )
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Partner"],
                         " and p.partner_id in (%s) " % self.vendor.id)
        self.assertEqual(parameters["p_User_ID"], str(self.env.user.id))
        self.assertEqual(parameters["p_Period_Start"], str(report.startdate))
        self.assertEqual(parameters["p_Period_End"], str(report.todate))
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(report.name, "Purchase Order By Period")

    def test_vendor_filter_empty_when_no_partner_selected(self):
        report = self.env["purchase.order.period.report"].create(
            {"partner": [(5, 0, 0)]}
        )
        self.assertEqual(report.get_parameters()["p_Partner"], " ")

    def test_action_clear_partner_drops_filter_and_reopens(self):
        report = self.env["purchase.order.period.report"].create(
            {"partner": [(6, 0, self.vendor.ids)]}
        )
        action = report.action_clear_partner()
        self.assertFalse(report.partner)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["res_model"], "purchase.order.period.report")
        self.assertEqual(action["res_id"], report.id)

    def test_wizard_view_is_the_default_form_view(self):
        view = self.env["purchase.order.period.report"].get_views(
            [[False, "form"]]
        )["views"]["form"]
        self.assertEqual(
            view["id"],
            self.env.ref(
                "od19_purchase_jasper.view_purchase_order_period_report"
            ).id,
        )


@tagged("post_install", "-at_install")
class TestPurchaseOrderOutstandingReport(TransactionCase):
    """r_p_003 Purchase Order Outstanding By Period."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Outstanding Vendor", "is_company": True, "supplier_rank": 1}
        )

    def test_default_jasper_file_points_to_purchase_order_outstanding_report(self):
        report = self.env["purchase.order.outstanding.report"].create({})
        self.assertTrue(
            report.jasper_file.endswith(
                "purchase_order_outstanding_report.jasper"
            )
        )
        self.assertTrue(
            os.path.isfile(report.get_jrxml_file()), report.get_jrxml_file()
        )

    def test_default_start_date_is_the_first_day_of_the_month(self):
        report = self.env["purchase.order.outstanding.report"].create({})
        self.assertEqual(report.startdate.day, 1)

    def test_show_picture_is_always_passed_as_string(self):
        report = self.env["purchase.order.outstanding.report"].create({})
        self.assertEqual(report.get_parameters()["p_Show_Picture"], "True")
        report.p_Show_Picture = False
        self.assertEqual(report.get_parameters()["p_Show_Picture"], "False")

    def test_vendor_filter_uses_a_alias_and_defaults_to_blank(self):
        report = self.env["purchase.order.outstanding.report"].create(
            {"partner": [(6, 0, self.vendor.ids)]}
        )
        self.assertEqual(
            report.get_parameters()["p_Partner"],
            " and a.partner_id in (%s) " % self.vendor.id,
        )
        report.partner = [(5, 0, 0)]
        self.assertEqual(report.get_parameters()["p_Partner"], " ")

    def test_wizard_view_is_the_default_form_view(self):
        view = self.env["purchase.order.outstanding.report"].get_views(
            [[False, "form"]]
        )["views"]["form"]
        self.assertEqual(
            view["id"],
            self.env.ref(
                "od19_purchase_jasper.view_purchase_order_outstanding_report"
            ).id,
        )


@tagged("post_install", "-at_install")
class TestReceivedPurchaseOrderPeriodReport(TransactionCase):
    """r_p_002 Received Purchase Order By Period."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Received Vendor", "is_company": True, "supplier_rank": 1}
        )

    def test_default_jasper_file_points_to_received_report(self):
        report = self.env["received.purchase.order.period.report"].create(
            {"partner": [(6, 0, self.vendor.ids)]}
        )
        self.assertTrue(
            report.jasper_file.endswith(
                "received_purchase_order_period_report.jasper"
            )
        )
        self.assertTrue(
            os.path.isfile(report.get_jrxml_file()), report.get_jrxml_file()
        )

    def test_vendor_parameter_uses_p_vendor_id_and_ai_alias(self):
        report = self.env["received.purchase.order.period.report"].create(
            {"partner": [(6, 0, self.vendor.ids)]}
        )
        parameters = report.get_parameters()
        self.assertIn("p_VendorID", parameters)
        self.assertNotIn("p_Partner", parameters)
        self.assertEqual(
            parameters["p_VendorID"],
            " and ai.partner_id in (%s)" % self.vendor.id,
        )

    def test_vendor_filter_empty_when_no_partner_selected(self):
        report = self.env["received.purchase.order.period.report"].create(
            {"partner": [(6, 0, self.vendor.ids)]}
        )
        report.partner = [(5, 0, 0)]
        self.assertEqual(report.get_parameters()["p_VendorID"], " ")

    def test_wizard_view_is_the_default_form_view(self):
        view = self.env["received.purchase.order.period.report"].get_views(
            [[False, "form"]]
        )["views"]["form"]
        self.assertEqual(
            view["id"],
            self.env.ref(
                "od19_purchase_jasper.view_received_purchase_order_period_report"
            ).id,
        )
