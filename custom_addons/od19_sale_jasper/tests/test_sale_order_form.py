import os

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestSaleOrderForm(TransactionCase):
    """F-S-002 Sale Order Form: the pilot form of the Sales Jasper module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Sale Form Partner", "is_company": True}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Sale Form Product", "list_price": 100.0}
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

    def _report(self, order=True, **values):
        report = self.env["sale.order.form"].create(values)
        if order:
            report = report.with_context(active_ids=self.order.ids)
        return report

    # ------------------------------------------------------------- shipping
    def test_default_jasper_file_is_shipped(self):
        report = self.env["sale.order.form"].create({})
        self.assertTrue(report.jasper_file.endswith("sale_order_form.jasper"))
        self.assertTrue(os.path.isfile(report.jasper_file), report.jasper_file)

    # ---------------------------------------------------- parameter contract
    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Where"], "WHERE so.id in (%s)" % self.order.id)
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
        # A falsy button return makes Odoo 19 close the dialog (see
        # action_service.js), which would hide the generated file.
        report = self._report()
        action = report._action_reopen_wizard()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["res_model"], "sale.order.form")
        self.assertEqual(action["res_id"], report.id)

    def test_wizard_view_is_the_default_form_view(self):
        # The concrete view extends the shared layout defined on
        # od19.jasper.report, another model.  Without mode="primary" Odoo does
        # not treat it as the default form view of sale.order.form, so
        # reopening the wizard falls back to the auto-generated view, which
        # carries no filename attribute and therefore loses the file name of
        # the generated PDF/XLSX.
        view = self.env["sale.order.form"].get_views([[False, "form"]])["views"]["form"]
        self.assertEqual(
            view["id"], self.env.ref("od19_sale_jasper.view_sale_order_form").id
        )
        self.assertIn('filename="name_pdf"', view["arch"])
        self.assertIn('filename="name_xlsx"', view["arch"])

    # ----------------------------------------------------------- validation
    def test_show_report_rejects_unapproved_order(self):
        draft = self.env["sale.order"].create({"partner_id": self.partner.id})
        report = self.env["sale.order.form"].with_context(
            active_ids=draft.ids
        ).create({})
        with self.assertRaises(ValidationError):
            report.show_report()
