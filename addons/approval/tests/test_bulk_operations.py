from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import common, tagged

from .common import ApprovalCommon, add_category_approver, record_approval


@tagged("post_install", "-at_install")
class TestBulkOperations(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin_user = cls.env.ref("base.user_admin")
        cls.approver1 = cls.env["res.users"].create(
            {
                "name": "Bulk Approver 1",
                "login": "bulk_approver1",
                "email": "bulk_approver1@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.approver2 = cls.env["res.users"].create(
            {
                "name": "Bulk Approver 2",
                "login": "bulk_approver2",
                "email": "bulk_approver2@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.non_approver = cls.env["res.users"].create(
            {
                "name": "Bulk Non Approver",
                "login": "bulk_non_approver",
                "email": "bulk_nonapprover@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0034",
                "name": "Test Bulk Operations Category",
                "approval_minimum": 1,
            }
        )

        add_category_approver(cls.category, cls.approver1, required=True)
        add_category_approver(cls.category, cls.approver2, required=False)

    def _create_test_requests(self, count=3):
        requests = self.env["approval.request"]
        for i in range(count):
            request = self.env["approval.request"].create(
                {
                    "name": f"Bulk Test Request {i + 1}",
                    "request_owner_id": self.admin_user.id,
                    "category_id": self.category.id,
                }
            )
            request.action_confirm()
            requests |= request
        return requests

    def test_bulk_approve_success_all_requests(self):
        requests = self._create_test_requests(3)

        self.assertTrue(
            all(r.state == "pending" for r in requests),
            "All requests should be pending before bulk approve",
        )

        result = requests.with_user(self.approver1).action_approve_bulk()

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("3", result["params"]["message"])

        self.assertTrue(
            all(r.state == "approved" for r in requests),
            "All requests should be approved after bulk approve",
        )

    def test_bulk_refuse_success_all_requests(self):
        requests = self._create_test_requests(3)

        self.assertTrue(
            all(r.state == "pending" for r in requests),
            "All requests should be pending before bulk refuse",
        )

        action = requests.with_user(self.approver1).action_refuse_bulk()
        self.assertEqual(action["res_model"], "approval.decision.wizard")
        self.assertEqual(action["context"]["default_decision_type"], "refuse")

        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver1)
            .with_context(action["context"])
            .create({})
        )
        with self.assertRaises(UserError):
            wizard.action_confirm_refuse()

        reason = self.env.ref("approval.refusal_reason_budget_exceeded")
        wizard.write({"refusal_reason_id": reason.id, "note": "over budget"})
        result = wizard.action_confirm_refuse()

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("3", result["params"]["message"])

        self.assertTrue(
            all(r.state == "refused" for r in requests),
            "All requests should be refused after bulk refuse",
        )
        self.assertEqual(requests.mapped("refusal_reason_id"), reason)
        self.assertEqual(set(requests.mapped("refusal_note")), {"over budget"})
        decided = requests.approver_ids.filtered(lambda a: a.decision_date)
        self.assertEqual(decided.mapped("refusal_reason_id"), reason)

    def test_bulk_approve_permission_denied_raises_error(self):
        requests = self._create_test_requests(2)

        with self.assertRaises(
            UserError, msg="Should raise UserError when user is not an approver"
        ):
            requests.with_user(self.non_approver).action_approve_bulk()

        self.assertTrue(
            all(r.state == "pending" for r in requests),
            "Requests should remain pending when permission denied",
        )

    def test_bulk_refuse_permission_denied_raises_error(self):
        requests = self._create_test_requests(2)

        with self.assertRaises(
            UserError, msg="Should raise UserError when user is not an approver"
        ):
            requests.with_user(self.non_approver).action_refuse_bulk()

        self.assertTrue(
            all(r.state == "pending" for r in requests),
            "Requests should remain pending when permission denied",
        )

    def test_bulk_approve_fails_when_approver_not_pending(self):
        request = self._create_test_requests(1)

        approver = request.approver_ids.filtered(lambda a: a.user_id == self.approver1)
        approver.sudo().write({"flow_state": "waiting"})

        with self.assertRaises(
            UserError,
            msg="Should raise UserError when approver state is not pending",
        ):
            request.with_user(self.approver1).action_approve_bulk()

    def test_bulk_operations_with_mixed_requests(self):
        category_no_approver1 = self.env["approval.category"].create(
            {
                "sequence_code": "SC0035",
                "name": "Test Category (no approver1)",
                "approval_minimum": 1,
            }
        )
        add_category_approver(category_no_approver1, self.approver2, required=True)

        request1 = self.env["approval.request"].create(
            {
                "name": "Request with approver1",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        request1.action_confirm()

        request2 = self.env["approval.request"].create(
            {
                "name": "Request with approver1 approved",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        request2.action_confirm()
        record_approval(
            request2.approver_ids.filtered(lambda a: a.user_id == self.approver1)
        )

        request3 = self.env["approval.request"].create(
            {
                "name": "Request without approver1",
                "request_owner_id": self.admin_user.id,
                "category_id": category_no_approver1.id,
            }
        )
        request3.action_confirm()

        all_requests = request1 | request2 | request3

        with self.assertRaises(
            UserError,
            msg="Should raise UserError when user lacks pending rights for some requests",
        ):
            all_requests.with_user(self.approver1).action_approve_bulk()

    def test_bulk_approve_upfront_validation_rejects_whole_batch(self):
        normal_requests = self._create_test_requests(2)

        failing_request = self.env["approval.request"].create(
            {
                "name": "Failing Request",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        failing_request.action_confirm()
        failing_request.approver_ids.sudo()._record_decision("refused")

        all_requests = normal_requests | failing_request

        with self.assertRaises(
            UserError,
            msg="Should raise UserError when trying to approve refused request",
        ):
            all_requests.with_user(self.approver1).action_approve_bulk()

        self.assertTrue(
            all(r.state == "pending" for r in normal_requests),
            "Upfront validation must reject the WHOLE batch atomically — "
            "the otherwise-valid requests must not be approved either.",
        )

    def test_bulk_approve_continues_after_mid_flight_failure(self):
        requests = self._create_test_requests(3)
        failing_request = requests[1]
        original_action_approve = type(requests).action_approve

        def patched_action_approve(rec):
            if rec.id == failing_request.id:
                raise UserError("Simulated mid-flight failure")
            return original_action_approve(rec)

        with patch.object(type(requests), "action_approve", patched_action_approve):
            result = requests.with_user(self.approver1).action_approve_bulk()

        failing_request.invalidate_recordset(["state"])
        self.assertEqual(
            failing_request.state,
            "pending",
            "The failing request must be left untouched, not half-decided.",
        )
        succeeded = requests - failing_request
        self.assertTrue(
            all(r.state == "approved" for r in succeeded),
            "The OTHER requests must still be approved despite the "
            "mid-flight failure on one of them.",
        )
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("2", result["params"]["message"])
        self.assertIn("Simulated mid-flight failure", result["params"]["message"])

    def test_bulk_operations_notification_message_format(self):
        requests = self._create_test_requests(5)

        result = requests.with_user(self.approver1).action_approve_bulk()

        self.assertIn("params", result)
        self.assertIn("message", result["params"])
        self.assertIn("type", result["params"])
        self.assertIn("next", result["params"])

        self.assertIn(
            "5",
            result["params"]["message"],
            "Notification should mention number of requests",
        )

        self.assertEqual(
            result["params"]["next"]["type"], "ir.actions.act_window_close"
        )

    def test_bulk_approve_single_request(self):
        request = self._create_test_requests(1)

        result = request.with_user(self.approver1).action_approve_bulk()

        self.assertEqual(request.state, "approved")
        self.assertIn("1", result["params"]["message"])

    def test_bulk_refuse_logs_message_to_chatter(self):
        requests = self._create_test_requests(2)

        message_counts_before = [len(r.message_ids) for r in requests]

        requests.with_user(self.approver1).action_approve_bulk()

        message_counts_after = [len(r.message_ids) for r in requests]

        for before, after in zip(
            message_counts_before, message_counts_after, strict=True
        ):
            self.assertGreater(
                after,
                before,
                "Bulk approve should post messages to chatter for audit trail",
            )

    def test_bulk_operations_with_empty_recordset(self):
        empty_requests = self.env["approval.request"]

        result = empty_requests.with_user(self.approver1).action_approve_bulk()

        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("0", result["params"]["message"])


@tagged("post_install", "-at_install")
class TestBatchCreateDoesNotSubscribePerRecord(ApprovalCommon):
    def test_batch_create_scales_sublinearly_in_queries(self):
        category = self._make_category(approvers=[self.approver_1])

        def create_n(count):
            self.env.invalidate_all()
            self.env.flush_all()
            before = self.env.cr.sql_statement_count
            self.env["approval.request"].create(
                [
                    {
                        "category_id": category.id,
                        "request_owner_id": self.owner_user.id,
                    }
                    for _ in range(count)
                ],
            )
            self.env.flush_all()
            return self.env.cr.sql_statement_count - before

        small = create_n(2)
        large = create_n(20)

        self.assertLess(
            large,
            small * 4,
            f"Creating 20 requests issued {large} queries against {small} "
            f"for 2 — follower subscription must be batched by owner, not "
            f"run once per record.",
        )

    def test_batch_create_subscribes_every_owner(self):
        category = self._make_category(approvers=[self.approver_1])
        requests = self.env["approval.request"].create(
            [
                {"category_id": category.id, "request_owner_id": owner.id}
                for owner in (self.owner_user, self.approver_2, self.owner_user)
            ],
        )

        for request, owner in zip(
            requests,
            (self.owner_user, self.approver_2, self.owner_user),
            strict=True,
        ):
            self.assertIn(
                owner.partner_id,
                request.message_partner_ids,
                f"{owner.name} must follow the request they own.",
            )


@tagged("post_install", "-at_install")
class TestUserIdsMirrorsApprovers(ApprovalCommon):
    def test_each_request_gets_its_own_approvers(self):
        shared = self._make_category(
            name="Shared Approvers",
            approvers=[self.approver_1, self.approver_2],
        )
        other = self._make_category(
            name="Other Approvers", approvers=[self.manager_user]
        )

        a = self._prepare_request(shared, confirm=False)
        b = self._prepare_request(shared, confirm=False)
        c = self._prepare_request(other, confirm=False)

        self.env.invalidate_all()
        (a | b | c).mapped("user_ids")

        self.assertEqual(a.user_ids, self.approver_1 | self.approver_2)
        self.assertEqual(b.user_ids, self.approver_1 | self.approver_2)
        self.assertEqual(c.user_ids, self.manager_user)

    def test_a_request_with_no_approvers_gets_an_empty_set(self):
        empty = self._make_category(name="No Approvers At All")
        request = self._prepare_request(empty, confirm=False)
        with_approvers = self._prepare_request(
            self._make_category(name="Has One", approvers=[self.approver_1]),
            confirm=False,
        )

        self.env.invalidate_all()
        (request | with_approvers).mapped("user_ids")

        self.assertFalse(request.user_ids)
        self.assertEqual(with_approvers.user_ids, self.approver_1)
