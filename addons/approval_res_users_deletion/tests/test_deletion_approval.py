from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestDeletionApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = new_test_user(
            cls.env,
            login="deletion_admin",
            groups="base.group_user,base.group_system",
            name="Admin",
        )
        cls.rule = cls.env.ref(
            "approval_res_users_deletion.approval_rule_account_deletion_self_service"
        )

    def _portal_user(self, login):
        return self.env["res.users"].create(
            {
                "name": "Portal",
                "login": login,
                "password": "password",
                "group_ids": [self.env.ref("base.group_portal").id],
            }
        )

    def _request_for(self, user):
        return self.env["res.users.deletion"].search([("user_id", "=", user.id)])

    def _run_cron(self):
        with self.enter_registry_test_mode():
            self.env.ref("base.ir_cron_res_users_deletion").method_direct_trigger()

    @mute_logger("odoo.addons.base.models.res_users_deletion")
    def test_self_service_deletion_is_approved_by_the_shipped_rule_and_runs(self):
        user = self._portal_user("portal_self")
        user.sudo()._deactivate_portal_user()
        deletion = self._request_for(user)
        self.assertEqual(deletion.approval_state, "approved")
        self.assertIn(self.rule, deletion.approval_request_id.applied_rule_ids)
        self._run_cron()
        self.assertFalse(user.exists())
        self.assertEqual(deletion.state, "done")

    @mute_logger("odoo.addons.base.models.res_users_deletion")
    def test_a_user_deleting_their_own_account_leaves_no_reference_to_it(self):
        user = self._portal_user("portal_leaving")
        user.with_user(user).sudo()._deactivate_portal_user()
        deletion = self._request_for(user)
        request = deletion.approval_request_id
        self.assertEqual(deletion.approval_state, "approved")
        self.assertNotEqual(request.request_owner_id, user)
        self.assertEqual(request.partner_id, user.partner_id)
        self.assertNotIn(user, request.decision_log_ids.user_id)

        self._run_cron()
        self.assertFalse(user.exists())
        self.assertEqual(deletion.state, "done")
        self.assertTrue(request.exists())

    @mute_logger("odoo.addons.base.models.res_users_deletion")
    def test_without_the_rule_an_administrator_decides(self):
        self.rule.active = False
        user = self._portal_user("portal_reviewed")
        user.sudo()._deactivate_portal_user()
        deletion = self._request_for(user)
        self.assertEqual(deletion.approval_state, "pending")
        self.assertIn(self.admin, deletion.pending_approver_ids)

        self._run_cron()
        self.assertTrue(user.exists(), "a pending request must not be executed")
        self.assertEqual(deletion.state, "todo")

        row = deletion.approval_request_id.approver_ids.filtered(
            lambda approver: approver.user_id == self.admin
        )
        row.with_user(self.admin).with_context(skip_wizard=True).action_approve()
        self.assertEqual(deletion.approval_state, "approved")
        self._run_cron()
        self.assertFalse(user.exists())

    @mute_logger("odoo.addons.base.models.res_users_deletion")
    def test_a_refused_request_keeps_the_archived_account(self):
        self.rule.active = False
        user = self._portal_user("portal_refused")
        user.sudo()._deactivate_portal_user()
        deletion = self._request_for(user)
        row = deletion.approval_request_id.approver_ids.filtered(
            lambda approver: approver.user_id == self.admin
        )
        row.with_user(self.admin).with_context(skip_wizard=True).action_refuse()
        self.assertEqual(deletion.approval_state, "refused")
        self.assertEqual(deletion.state, "refused")
        self._run_cron()
        self.assertTrue(user.exists())
        self.assertFalse(user.active)

    def test_a_queued_request_from_before_the_bridge_still_runs(self):
        user = self._portal_user("portal_legacy")
        user.action_archive()
        deletion = (
            self.env["res.users.deletion"]
            .with_context(approval_skip=True)
            .create({"user_id": user.id, "state": "todo"})
        )
        self.assertFalse(deletion.approval_request_id)
        with mute_logger("odoo.addons.base.models.res_users_deletion"):
            self._run_cron()
        self.assertFalse(user.exists())
