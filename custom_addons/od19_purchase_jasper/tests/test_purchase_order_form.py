import os

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseOrderForm(TransactionCase):
    """F-P-003 Purchase Order Form: the pilot form of the Purchase module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Purchase Form Vendor", "is_company": True}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Purchase Form Product", "purchase_ok": True}
        )
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        cls.order.action_od19_submit_for_approval()
        cls.order.action_od19_approve()
        cls.order.button_confirm()

    def _report(self, order=True, **values):
        report = self.env["purchase.order.form"].create(values)
        if order:
            report = report.with_context(active_ids=self.order.ids)
        return report

    # ------------------------------------------------------------- shipping
    def test_default_jasper_file_points_to_purchase_order_report(self):
        report = self.env["purchase.order.form"].create({})
        self.assertTrue(
            report.jasper_file.endswith("purchase_order_report.jasper")
        )
        self.assertTrue(
            os.path.isfile(report.get_jrxml_file()), report.get_jrxml_file()
        )

    # ---------------------------------------------------- parameter contract
    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Where"], "WHERE po.id in (%s)" % self.order.id
        )
        self.assertEqual(parameters["p_ISO"], "")
        self.assertTrue(parameters["p_Path"].endswith("/"))
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(report.name, self.order.display_name)

    def test_locale_follows_date_type(self):
        report = self._report(date_type="BE")
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_signature_toggles_flow_to_parameters(self):
        report = self._report(p_EName=False, p_ESignature=False)
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_EName"], "False")
        self.assertEqual(parameters["p_ESignature"], "False")

    def test_language_flows_to_parameters(self):
        report = self._report(p_language="english")
        self.assertEqual(report.get_parameters()["p_language"], "english")

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(order=False).get_parameters()

    # --------------------------------------------------------------- email
    def test_partner_ids_for_send_by_email(self):
        report = self._report()
        self.assertEqual(report.get_partner_ids_for_send_by_email(), self.partner)

    # ------------------------------------------------------------- lifecycle
    def test_reopen_wizard_action_keeps_the_dialog_open(self):
        report = self._report()
        action = report._action_reopen_wizard()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["res_model"], "purchase.order.form")
        self.assertEqual(action["res_id"], report.id)

    def test_wizard_view_is_the_default_form_view(self):
        view = self.env["purchase.order.form"].get_views([[False, "form"]])[
            "views"
        ]["form"]
        self.assertEqual(
            view["id"],
            self.env.ref("od19_purchase_jasper.view_purchase_order_form").id,
        )
        self.assertIn('filename="name_pdf"', view["arch"])
        self.assertIn('filename="name_xlsx"', view["arch"])

    # ----------------------------------------------------------- validation
    def test_show_report_rejects_unapproved_order(self):
        draft = self.env["purchase.order"].create({"partner_id": self.partner.id})
        report = self.env["purchase.order.form"].with_context(
            active_ids=draft.ids
        ).create({})
        with self.assertRaises(ValidationError):
            report.show_report()
