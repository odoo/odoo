from datetime import date, timedelta

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestDecisionLog(ApprovalCommon):
    """What was decided survives what the request later becomes.

    The approver rows hold the current decision and are rewritten by a
    withdrawal, a reset or a revocation. The log holds every decision ever
    taken, who took it, on whose behalf and under what elevation, and it cannot
    be changed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_3 = cls.env["res.users"].create(
            {
                "name": "Ledger Delegate",
                "login": "ledger_delegate",
                "email": "ledger_delegate@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.category = cls._make_category(
            "Ledger",
            approvers=[(cls.approver_1, True, 10), (cls.approver_2, True, 20)],
        )

    def _row(self, request, user):
        return request.approver_ids.filtered(lambda a: a.user_id == user)

    def _decide(self, request, user, verdict, actor=None):
        row = self._row(request, user).with_user(actor or user)
        getattr(row.with_context(skip_wizard=True), f"action_{verdict}")()

    def _facts(self, request):
        return [
            (log.verdict, log.user_id, log.principal_id, log.elevation)
            for log in request.decision_log_ids.sorted("id")
        ]

    def test_a_decision_is_logged_with_its_actor(self):
        request = self._prepare_request(self.category)
        self._decide(request, self.approver_1, "approve")
        log = request.decision_log_ids
        self.assertEqual(len(log), 1)
        self.assertEqual(
            (log.verdict, log.user_id, log.approver_id, log.elevation),
            ("approved", self.approver_1, self._row(request, self.approver_1), "none"),
        )

    def test_a_reset_erases_the_rows_but_not_the_history(self):
        request = self._prepare_request(self.category)
        self._decide(request, self.approver_1, "approve")
        self._decide(request, self.approver_2, "refuse")
        self.assertEqual(request.state, "refused")
        request.with_user(self.manager_user).action_reset_to_draft()
        self.assertFalse(request.approver_ids.decided_by_user_id)
        self.assertEqual(
            [fact[0] for fact in self._facts(request)],
            ["approved", "refused", "reset"],
        )
        self.assertEqual(
            request.decision_log_ids.filtered(
                lambda log: log.verdict == "reset"
            ).user_id,
            self.manager_user,
        )

    def test_a_withdrawal_is_a_fact_not_an_erasure(self):
        request = self._prepare_request(self.category)
        self._decide(request, self.approver_1, "approve")
        request.with_user(self.approver_1).action_withdraw()
        self.assertEqual(self._row(request, self.approver_1).state, "pending")
        self.assertEqual(
            [fact[0] for fact in self._facts(request)], ["approved", "withdrawn"]
        )

    def test_a_delegate_is_logged_acting_for_the_approver(self):
        request = self._prepare_request(self.category)
        today = date.today()
        self._row(request, self.approver_1).sudo().write(
            {
                "delegate_id": self.approver_3.id,
                "delegate_start_date": today - timedelta(days=1),
                "delegate_end_date": today + timedelta(days=1),
            }
        )
        self._decide(request, self.approver_1, "approve", actor=self.approver_3)
        self.assertEqual(
            self._facts(request),
            [("approved", self.approver_3, self.approver_1, "none")],
        )

    def test_an_elevated_decision_says_so(self):
        request = self._prepare_request(self.category)
        self._row(request, self.approver_1).with_user(
            self.approver_1
        ).sudo().with_context(skip_wizard=True).action_approve()
        self.assertEqual(request.decision_log_ids.elevation, "self_elevated")

    def test_a_grant_and_a_revocation_are_logged(self):
        request = self._prepare_request(self.category)
        request.with_user(self.manager_user)._approve_without_decision("granted")
        request.with_user(self.manager_user)._revoke("cancelled", "revoked")
        self.assertEqual(
            [fact[0] for fact in self._facts(request)], ["granted", "revoked"]
        )

    def test_the_log_cannot_be_changed_or_deleted_even_by_the_superuser(self):
        request = self._prepare_request(self.category)
        self._decide(request, self.approver_1, "approve")
        log = request.decision_log_ids.sudo()
        with self.assertRaises(UserError):
            log.write({"verdict": "refused"})
        with self.assertRaises(UserError):
            log.unlink()

    def test_the_history_is_read_through_the_request(self):
        request = self._prepare_request(self.category)
        self._decide(request, self.approver_1, "approve")
        as_owner = request.with_user(self.owner_user)
        self.assertEqual(len(as_owner.decision_log_ids), 1)
        self.assertEqual(
            self.env["approval.decision.log"].with_user(self.owner_user).search([]),
            request.decision_log_ids,
        )

    def test_the_form_shows_the_history_to_an_approver_who_is_no_manager(self):
        request = self._prepare_request(self.category)
        self._decide(request, self.approver_1, "approve")
        [values] = request.with_user(self.approver_2).web_read(
            {"decision_log_ids": {"fields": {"verdict": {}, "user_id": {}}}}
        )
        self.assertEqual(
            [log["verdict"] for log in values["decision_log_ids"]], ["approved"]
        )

    def test_the_history_of_a_request_you_cannot_read_stays_hidden(self):
        request = self._prepare_request(self.category)
        self._decide(request, self.approver_1, "approve")
        log = request.decision_log_ids
        Log = self.env["approval.decision.log"].with_user(self.approver_3)
        self.assertFalse(Log.search([]))
        self.assertFalse(Log.search_count([("id", "=", log.id)]))
        with self.assertRaises(AccessError):
            log.with_user(self.approver_3).read(["verdict"])
