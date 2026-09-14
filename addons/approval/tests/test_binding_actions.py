from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import add_category_approver


@tagged("post_install", "-at_install")
class TestApprovalBindingActions(common.TransactionCase):
    """Gating actions on the server, where web_studio gated them only in the browser.

    A web_studio approval rule on a server action was checked by the client before
    executing, so an RPC caller running the action directly ran it unchecked --
    demonstrated on a disposable database. These pin that a binding on a server
    action or a report refuses on the server, and say which actions cannot be.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Binding = cls.env["approval.binding"]
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        groups = [
            cls.env.ref("base.group_user").id,
            cls.env.ref("base.group_partner_manager").id,
        ]
        cls.approver, cls.requester = (
            cls.env["res.users"].create(
                {
                    "name": name,
                    "login": login,
                    "email": f"{login}@test.com",
                    "group_ids": [(6, 0, groups)],
                }
            )
            for name, login in (
                ("Action Approver", "action_approver"),
                ("Action Requester", "action_requester"),
            )
        )
        cls.category = cls.env["approval.category"].create(
            {
                "name": "Action Category",
                "approval_minimum": 1,
                "allow_self_approval": True,
            }
        )
        add_category_approver(cls.category, cls.approver, required=True, sequence=10)
        cls.server_action = cls.env["ir.actions.server"].create(
            {
                "name": "Mark reviewed",
                "model_id": cls.partner_model.id,
                "state": "code",
                "code": "records.write({'comment': 'ACTION RAN'})",
            }
        )
        cls.env["ir.ui.view"].create(
            {
                "name": "approval_action_probe_report",
                "type": "qweb",
                "key": "approval.action_probe_report",
                "arch": '<t t-name="approval.action_probe_report">'
                '<t t-foreach="docs" t-as="doc"><span t-out="doc.name"/></t></t>',
            }
        )
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "Probe report",
                "model": "res.partner",
                "report_type": "qweb-html",
                "report_name": "approval.action_probe_report",
            }
        )

    def tearDown(self):
        self.Binding._unregister_hook()
        super().tearDown()

    def _bind(self, action, **vals):
        return self.Binding.create(
            {
                "model_id": self.partner_model.id,
                "action_id": action.id,
                "category_id": self.category.id,
                **vals,
            }
        )

    def _partner(self):
        return self.env["res.partner"].create(
            {"name": "Action Partner", "comment": "untouched"}
        )

    def _run(self, user, partner):
        return (
            self.server_action.with_user(user)
            .with_context(
                active_model="res.partner",
                active_id=partner.id,
                active_ids=[partner.id],
            )
            .run()
        )

    def _ran(self, partner):
        partner.invalidate_recordset()
        return "ACTION RAN" in (partner.comment or "")

    def _requests_for(self, partner):
        return self.env["approval.request"].search(
            [("res_model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )

    # -- server actions ----------------------------------------------------

    def test_a_blocked_server_action_is_refused_on_the_server(self):
        """Exactly the call web_studio let through."""
        self._bind(self.server_action, mode="block", sudo_policy="enforce")
        partner = self._partner()
        with self.assertRaises(UserError):
            self._run(self.requester, partner)
        self.assertFalse(self._ran(partner))

    def test_a_request_mode_server_action_asks_instead_of_running(self):
        self._bind(self.server_action, mode="request")
        partner = self._partner()
        action = self._run(self.requester, partner)
        self.assertFalse(self._ran(partner))
        self.assertEqual(action["res_model"], "approval.request")
        self.assertEqual(self._requests_for(partner).state, "pending")

    def test_approving_runs_the_server_action_once_as_the_requester(self):
        self._bind(self.server_action, mode="request")
        partner = self._partner()
        self._run(self.requester, partner)
        request = self._requests_for(partner)
        request.with_user(self.approver).action_approve()
        self.assertTrue(self._ran(partner))
        self.assertEqual(partner.write_uid, self.requester)
        self.assertTrue(request.date_binding_replayed)

    def test_an_approver_invoking_a_server_action_runs_it(self):
        self._bind(self.server_action, mode="request", approve_on_invoke=True)
        partner = self._partner()
        self._run(self.approver, partner)
        self.assertTrue(self._ran(partner))
        self.assertEqual(self._requests_for(partner).state, "approved")

    # -- reports -----------------------------------------------------------

    def _render_html(self, user, partner):
        return (
            self.env["ir.actions.report"]
            .with_user(user)
            ._render_qweb_html(self.report.id, [partner.id])
        )

    def test_a_report_refuses_to_render_an_uncovered_record(self):
        self._bind(self.report, mode="block", sudo_policy="enforce")
        partner = self._partner()
        with self.assertRaises(UserError):
            self._render_html(self.requester, partner)

    def test_the_pdf_entry_point_is_gated_too(self):
        """A stored PDF is returned without rendering, so the check sits at the entry."""
        self._bind(self.report, mode="block", sudo_policy="enforce")
        partner = self._partner()
        with self.assertRaises(UserError):
            self.env["ir.actions.report"].with_user(self.requester)._render_qweb_pdf(
                self.report.id, [partner.id]
            )

    def test_a_report_renders_once_an_approved_request_covers_the_record(self):
        self._bind(self.report, mode="block", sudo_policy="enforce")
        partner = self._partner()
        request = self.env["approval.request"].create(
            {
                "name": "Printing approved",
                "category_id": self.category.id,
                "request_owner_id": self.requester.id,
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        request.action_confirm()
        request.with_user(self.approver).action_approve()
        html, report_type = self._render_html(self.requester, partner)
        self.assertEqual(report_type, "html")
        self.assertIn(b"Action Partner", html)

    # -- what can and cannot be enforced -----------------------------------

    def test_is_enforced_says_which_operations_the_server_can_refuse(self):
        window = self.env.ref("base.action_partner_form")
        self.assertTrue(self._bind(self.server_action, mode="advise").is_enforced)
        self.assertTrue(self._bind(self.report, mode="advise").is_enforced)
        self.assertFalse(
            self._bind(window, mode="advise").is_enforced,
            "opening a view is nothing the server can intercept",
        )

    def test_a_binding_gates_a_method_or_an_action_never_both(self):
        with self.assertRaises(ValidationError):
            self.Binding.create(
                {
                    "model_id": self.partner_model.id,
                    "method": "action_archive",
                    "action_id": self.server_action.id,
                }
            )
        with self.assertRaises(ValidationError):
            self.Binding.create({"model_id": self.partner_model.id})

    def test_a_report_cannot_wait_for_an_approval(self):
        with self.assertRaises(ValidationError):
            self._bind(self.report, mode="request", run_on_approval=False)

    def test_a_server_action_of_another_model_is_refused(self):
        users_action = self.env["ir.actions.server"].create(
            {
                "name": "On users",
                "model_id": self.env["ir.model"]._get("res.users").id,
                "state": "code",
                "code": "pass",
            }
        )
        with self.assertRaises(ValidationError):
            self._bind(users_action, mode="advise")

    def test_only_a_server_action_is_run_again_on_approval(self):
        window = self.env.ref("base.action_partner_form")
        with self.assertRaises(ValidationError):
            self._bind(window, mode="request")
        self.assertTrue(self._bind(window, mode="request", run_on_approval=False))

    def test_two_actions_on_one_model_may_each_have_a_binding(self):
        second = self.env["ir.actions.server"].create(
            {
                "name": "Second action",
                "model_id": self.partner_model.id,
                "state": "code",
                "code": "pass",
            }
        )
        self._bind(self.server_action, mode="advise")
        self.assertTrue(self._bind(second, mode="advise"))
