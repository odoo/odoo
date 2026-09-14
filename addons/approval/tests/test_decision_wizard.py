from odoo.exceptions import UserError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import add_category_approver


@tagged("post_install", "-at_install")
class TestDecisionWizard(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.admin_user = self.env.ref("base.user_admin")
        self.approver_user = self.env["res.users"].create(
            {
                "name": "Test Approver",
                "login": "test_approver_wizard",
                "email": "approver_wizard@test.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        self.category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0038",
                "name": "Test Wizard Category",
                "approval_minimum": 1,
            }
        )

        add_category_approver(self.category, self.approver_user, required=True)

        self.refusal_reason1 = self.env["approval.refusal.reason"].create(
            {
                "name": "Insufficient Information",
                "description": "The request lacks necessary details.",
            }
        )
        self.refusal_reason2 = self.env["approval.refusal.reason"].create(
            {
                "name": "Budget Constraints",
                "description": "Exceeds approved budget allocation.",
            }
        )

    def _create_pending_request(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Request for Wizard",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        request.action_confirm()
        return request

    def test_approve_is_one_click(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approver.with_user(self.approver_user).action_approve()
        self.assertEqual(approver.state, "approved")

    def test_refusal_wizard_opens_from_action_refuse(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        action = approver.with_user(self.approver_user).action_refuse()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "approval.decision.wizard")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["target"], "new")

        self.assertEqual(action["context"]["default_approver_id"], approver.id)
        self.assertEqual(action["context"]["default_decision_type"], "refuse")

        self.assertEqual(approver.state, "pending")

    def test_refusal_wizard_requires_reason(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                    "note": "Some additional notes",
                }
            )
        )

        with self.assertRaises(
            UserError,
            msg="Should raise UserError when refusal reason not selected",
        ):
            wizard.action_confirm_refuse()

        self.assertEqual(approver.state, "pending")

    def test_refusal_wizard_saves_reason_and_note(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                    "refusal_reason_id": self.refusal_reason1.id,
                    "note": "Missing cost breakdown and timeline",
                }
            )
        )

        wizard.action_confirm_refuse()

        self.assertEqual(approver.state, "refused")

        self.assertEqual(
            approver.refusal_reason_id,
            self.refusal_reason1,
            "Refusal reason should be saved",
        )

        self.assertEqual(approver.note, "Missing cost breakdown and timeline")

    def test_wizard_validation_state_not_pending(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approver.sudo().write({"flow_state": "waiting"})
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                    "refusal_reason_id": self.refusal_reason1.id,
                }
            )
        )
        with self.assertRaises(UserError):
            wizard.action_confirm_refuse()

    def test_wizard_action_cancel_closes_without_changes(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                    "note": "Should not be saved",
                }
            )
        )
        action = wizard.action_cancel()
        self.assertEqual(action["type"], "ir.actions.act_window_close")
        self.assertEqual(approver.state, "pending")
        self.assertFalse(approver.note)

    def test_refusal_wizard_returns_close_action(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                    "refusal_reason_id": self.refusal_reason1.id,
                    "note": "Test",
                }
            )
        )
        result = wizard.action_confirm_refuse()
        self.assertEqual(result, {"type": "ir.actions.act_window_close"})

    def test_wizard_refusal_reason_does_not_autofill_note(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                }
            )
        )
        self.assertFalse(wizard.note)

        wizard.refusal_reason_id = self.refusal_reason1
        self.assertFalse(
            wizard.note,
            "refusal_note must stay user-driven; the reason description "
            "is surfaced separately via refusal_reason_description.",
        )

        self.assertEqual(
            wizard.refusal_reason_description,
            self.refusal_reason1.description,
        )

    def test_wizard_displays_context_information(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                }
            )
        )
        self.assertEqual(wizard.request_id, request)
        self.assertEqual(wizard.request_name, request.name)
        self.assertEqual(wizard.request_owner_id, request.request_owner_id)
        self.assertEqual(wizard.category_id, request.category_id)
        self.assertEqual(wizard.user_id, approver.user_id)

    def test_refusal_note_optional_when_reason_provided(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                    "refusal_reason_id": self.refusal_reason1.id,
                }
            )
        )

        wizard.action_confirm_refuse()

        self.assertEqual(approver.state, "refused")
        self.assertEqual(approver.refusal_reason_id, self.refusal_reason1)

        self.assertFalse(approver.note)

    def test_header_refuse_opens_wizard(self):
        request = self._create_pending_request()
        action = request.with_user(self.approver_user).action_refuse()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "approval.decision.wizard")
        self.assertEqual(action["context"]["default_decision_type"], "refuse")
        self.assertIn("default_approver_id", action["context"])

    def test_action_cancel_is_owner_scoped(self):
        from odoo.exceptions import AccessError

        request = self._create_pending_request()
        with self.assertRaises(AccessError):
            request.with_user(self.approver_user).action_cancel()

    def test_refuse_persists_reason_on_request(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "refuse",
                    "refusal_reason_id": self.refusal_reason1.id,
                    "note": "Need quote from second vendor",
                }
            )
        )
        wizard.action_confirm_refuse()
        self.assertEqual(request.state, "refused")
        self.assertEqual(request.refusal_reason_id, self.refusal_reason1)
        self.assertEqual(request.refusal_note, "Need quote from second vendor")
