from odoo import fields
from odoo.tests import common, tagged

from .common import ApprovalCommon, add_category_approver, new_trip_category


@tagged("post_install", "-at_install")
class TestApprovalInsights(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Insights Approver",
                "login": "insights_approver",
                "email": "insights_approver@test.com",
            }
        )
        cls.owner = cls.env.ref("base.user_admin")
        cls.category = new_trip_category(cls.env)
        cls.category.write(
            {
                "approval_minimum": 1,
            }
        )
        add_category_approver(
            cls.category, cls.approver_user, required=True, sequence=10
        )

    def _create_request(self, **kwargs):
        vals = {
            "name": "Test Request",
            "category_id": self.category.id,
            "request_owner_id": self.owner.id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
        }
        vals.update(kwargs)
        return self.env["approval.request"].create(vals)

    def _create_and_approve(self, **kwargs):
        request = self._create_request(**kwargs)
        request.action_confirm()
        request.with_user(self.approver_user).action_approve()
        self.assertEqual(request.state, "approved")
        return request

    def _create_and_refuse(self, **kwargs):
        request = self._create_request(**kwargs)
        request.action_confirm()
        request.with_user(self.approver_user).with_context(
            skip_wizard=True
        ).action_refuse()
        self.assertEqual(request.state, "refused")
        return request

    def test_prediction_uncertain_with_no_history(self):
        request = self._create_request(amount=500.0)
        self.assertEqual(request._predict_outcome()[0], "uncertain")
        self.assertEqual(request._predict_outcome()[1], 0.0)

    def test_prediction_approve_with_strong_history(self):
        for _ in range(4):
            self._create_and_approve(amount=500.0)
        self._create_and_refuse(amount=500.0)

        request = self._create_request(amount=500.0)
        self.assertEqual(request._predict_outcome()[0], "approve")
        self.assertGreaterEqual(request._predict_outcome()[1], 0.75)

    def test_prediction_refuse_with_rejection_history(self):
        self._create_and_approve(amount=500.0)
        for _ in range(4):
            self._create_and_refuse(amount=500.0)

        request = self._create_request(amount=500.0)
        self.assertEqual(request._predict_outcome()[0], "refuse")
        self.assertGreaterEqual(request._predict_outcome()[1], 0.75)

    def test_prediction_skipped_for_terminal_states(self):
        request = self._create_and_approve(amount=500.0)
        self.assertFalse(request._predict_outcome()[0])

    def test_snapshot_captured_on_confirm(self):
        request = self._create_request(amount=100.0)
        self.assertFalse(request.category_snapshot)

        request.action_confirm()
        snapshot = request.category_snapshot
        self.assertIsInstance(snapshot, dict)
        self.assertEqual(snapshot["category_name"], self.category.name)
        self.assertEqual(snapshot["approval_minimum"], self.category.approval_minimum)

    def test_snapshot_preserves_the_steps_and_who_they_ask(self):
        request = self._create_request(amount=100.0)
        request.action_confirm()

        (step,) = request.category_snapshot["steps"]
        self.assertEqual(step["members"], [self.approver_user.id])
        approvers = request.category_snapshot["effective_approvers"]
        self.assertEqual(len(approvers), 1)
        self.assertEqual(approvers[0]["user_id"], self.approver_user.id)
        self.assertTrue(approvers[0]["required"])

    def test_snapshot_survives_category_change(self):
        request = self._create_request(amount=100.0)
        request.action_confirm()

        original_minimum = request.category_snapshot["approval_minimum"]
        self.category.approval_minimum = 5

        self.assertEqual(
            request.category_snapshot["approval_minimum"], original_minimum
        )


@tagged("post_install", "-at_install")
class TestApprovalInsightsAuditRegressions(ApprovalCommon):
    def test_m3_predicted_outcome_batches_queries_across_rows(self):
        category = self._make_category(
            approvers=[self.approver_1],
        )

        requests = self.env["approval.request"].create(
            [
                {
                    "name": f"M3 Request {i}",
                    "request_owner_id": self.owner_user.id,
                    "category_id": category.id,
                    "amount": 100.0 + i,
                }
                for i in range(5)
            ]
        )

        self.env.invalidate_all()
        self.env.flush_all()

        queries_before = self.env.cr.sql_statement_count
        requests._predict_outcomes()
        queries_issued = self.env.cr.sql_statement_count - queries_before
        self.assertLessEqual(
            queries_issued,
            3,
            f"Predicting 5 requests issued "
            f"{queries_issued} queries; the batched compute should "
            f"cache per-(category, partner) and keep this close to 1.",
        )


@tagged("post_install", "-at_install")
class TestPredictionExcludesNonDecisions(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            name="Prediction Cat",
            approvers=[(cls.approver_1, False, 10)],
        )

    def _resolved(self, outcome, amount=100.0):
        request = self._prepare_request(self.category, amount=amount)
        if outcome == "approved":
            request.with_user(self.approver_1).with_context(
                skip_wizard=True,
            ).action_approve()
        elif outcome == "refused":
            request.with_user(self.approver_1).with_context(
                skip_wizard=True,
            ).action_refuse()
        elif outcome == "cancelled":
            request.with_user(self.owner_user).action_cancel()
        return request

    def _prediction_for_a_new_request(self):
        request = self._prepare_request(self.category, confirm=False, amount=100.0)
        request.invalidate_recordset()
        return request._predict_outcome()[0], request._predict_outcome()[1]

    def test_cancellations_do_not_dilute_a_clean_approval_record(self):
        for _ in range(5):
            self._resolved("approved")
        for _ in range(5):
            self._resolved("cancelled")

        outcome, confidence = self._prediction_for_a_new_request()

        self.assertEqual(
            outcome,
            "approve",
            "5 approvals and 5 cancellations is a 100%% approval rate "
            "among real decisions, not a coin flip.",
        )
        self.assertEqual(confidence, 1.0)

    def test_refusals_still_count(self):
        for _ in range(4):
            self._resolved("refused")
        self._resolved("approved")

        outcome, _confidence = self._prediction_for_a_new_request()

        self.assertEqual(outcome, "refuse")

    def test_cancellations_alone_leave_the_prediction_unknown(self):
        for _ in range(5):
            self._resolved("cancelled")

        outcome, confidence = self._prediction_for_a_new_request()

        self.assertEqual(outcome, "uncertain")
        self.assertEqual(confidence, 0.0)


@tagged("post_install", "-at_install")
class TestPredictionOnNegativeAmounts(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            name="Refund Cat",
            approvers=[(cls.approver_1, False, 10)],
        )

    def _approved(self, amount):
        request = self._prepare_request(self.category, amount=amount)
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()
        return request

    def _prediction_for(self, amount):
        request = self._prepare_request(self.category, confirm=False, amount=amount)
        request.invalidate_recordset()
        return request._predict_outcome()[0], request._predict_outcome()[1]

    def test_negative_amounts_predict_from_their_own_history(self):
        for _ in range(5):
            self._approved(-1000.0)

        outcome, confidence = self._prediction_for(-1000.0)

        self.assertEqual(
            outcome,
            "approve",
            "Five approved -1000 requests are a perfect record; the "
            "similarity band must not invert on negative amounts.",
        )
        self.assertEqual(confidence, 1.0)

    def test_negative_band_still_excludes_dissimilar_amounts(self):
        for _ in range(5):
            self._approved(-1000.0)

        outcome, confidence = self._prediction_for(-50.0)

        self.assertEqual(outcome, "uncertain")
        self.assertEqual(confidence, 0.0)
