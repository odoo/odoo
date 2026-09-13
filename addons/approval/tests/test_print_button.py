from lxml import etree

from odoo.tests import tagged

from .common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestPrintButtonVisibility(ApprovalCommon):
    def test_the_form_header_leaves_printing_to_the_gear_menu(self):
        view = self.env.ref("approval.view_approval_request_form")
        arch = etree.fromstring(view.arch)
        report = self.env.ref("approval.action_report_approval_request")
        self.assertFalse(arch.xpath('//header/button[@name="%d"]' % report.id))

    def test_the_print_report_is_offered_for_approved_requests_of_any_type(self):
        category = self._make_category(
            name=f"Print Gear Cat {self.id()}",
            approvers=[self.approver_1],
            approval_type="general",
        )
        request = self._prepare_request(category)
        report = self.env.ref("approval.action_report_approval_request")
        self.assertFalse(
            report.get_valid_action_reports("approval.request", request.ids)
        )
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(
            report.get_valid_action_reports("approval.request", request.ids),
            report.ids,
        )

    def test_print_report_binding_is_generic_for_any_approval_type(self):
        report = self.env.ref("approval.action_report_approval_request")
        self.assertEqual(report.binding_type, "report")
        self.assertEqual(report.binding_model_id.model, "approval.request")

    def test_approval_product_report_template_extension_unaffected(self):
        module = (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "approval_product"), ("state", "=", "installed")])
        )
        if not module:
            self.skipTest("approval_product not installed")
        extension = self.env.ref(
            "approval_product.report_approval_request_document_products"
        )
        self.assertEqual(
            extension.inherit_id,
            self.env.ref("approval.report_approval_request_document"),
        )

    def test_general_type_request_reaches_approved_state(self):
        category = self._make_category(
            name=f"Print Button Cat {self.id()}",
            approvers=[self.approver_1],
            approval_type="general",
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.approval_type, "general")
