from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, common, tagged

from .common import (
    ApprovalCommon,
    add_category_approver,
    new_trip_category,
    pool_step,
    record_approval,
)


@tagged("post_install", "-at_install")
class TestRequest(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user_1 = cls.env["res.users"].create(
            {
                "name": "Test Approver 1",
                "login": "test_approver_1",
                "email": "approver1@test.com",
            }
        )
        cls.approver_user_2 = cls.env["res.users"].create(
            {
                "name": "Test Approver 2",
                "login": "test_approver_2",
                "email": "approver2@test.com",
            }
        )

    def test_compute_state(self):
        category_test = self.env["approval.category"].create(
            {
                "name": "Compute State Cat",
                "sequence_code": "CSC01",
                "step_ids": pool_step([], minimum=1),
            }
        )
        requester_user = self.env.ref("base.user_admin")
        requester_user.sudo().write(
            {
                "group_ids": [
                    Command.link(self.env.ref("approval.group_approval_manager").id),
                ],
            },
        )
        record = self.env["approval.request"].create(
            {
                "name": "test request",
                "request_owner_id": requester_user.id,
                "category_id": category_test.id,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now(),
            }
        )
        first_approver = self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": record.id,
                "flow_state": "new",
            }
        )
        second_approver = self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_2.id,
                "request_id": record.id,
                "flow_state": "new",
            }
        )
        record.approver_ids = first_approver | second_approver

        self.assertEqual(record.state, "new")

        record.action_confirm()

        self.assertEqual(record.state, "pending")
        record.action_approve(first_approver)
        self.assertEqual(record.state, "approved")
        self.assertEqual(second_approver.state, "waiting")
        with self.assertRaises(UserError):
            record.action_approve(second_approver)
        with self.assertRaises(UserError):
            record.with_context(skip_wizard=True).action_refuse(second_approver)
        self.assertEqual(record.state, "approved")

        record.action_withdraw(first_approver)
        self.assertEqual(record.state, "pending")
        self.assertEqual(second_approver.state, "pending")
        record.action_refuse(first_approver)
        self.assertEqual(record.state, "refused")

        with self.assertRaises(UserError):
            record.action_withdraw(first_approver)

        record.action_reset_to_draft()
        self.assertEqual(record.state, "new")
        self.assertFalse(record.refusal_reason_id)
        self.assertFalse(record.date_refused)
        self.assertFalse(record.date_confirmed)
        self.assertTrue(all(a.state == "new" for a in record.approver_ids))

        category_test.step_ids.minimum = 2
        record.action_confirm()
        self.assertEqual(record.state, "pending")
        record.action_approve(first_approver)
        self.assertEqual(record.state, "pending")
        record.action_approve(second_approver)
        self.assertEqual(record.state, "approved")
        record.action_withdraw(second_approver)
        self.assertEqual(record.state, "pending")
        record.action_refuse(second_approver)
        self.assertEqual(record.state, "refused")

        self.assertEqual(first_approver.state, "approved")
        self.assertEqual(second_approver.state, "refused")

    def test_compute_state_with_required(self):
        category_test = self.env["approval.category"].create(
            {
                "name": "Compute State Required Cat",
                "sequence_code": "CSC02",
                "approval_minimum": 1,
            }
        )
        add_category_approver(
            category_test, self.approver_user_1, required=True, sequence=10
        )
        add_category_approver(
            category_test, self.approver_user_2, required=False, sequence=20
        )
        requester_user = self.env.ref("base.user_admin")
        record = self.env["approval.request"].create(
            {
                "name": "test request",
                "request_owner_id": requester_user.id,
                "category_id": category_test.id,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now(),
            }
        )
        first_approver = record.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user_1,
        )
        second_approver = record.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user_2,
        )

        self.assertEqual(record.state, "new")

        record.action_confirm()

        self.assertEqual(record.state, "pending")
        record.action_approve(second_approver)
        self.assertEqual(record.state, "pending")
        record.action_approve(first_approver)
        self.assertEqual(record.state, "approved")

        category_test.step_ids.minimum = 2
        record.action_withdraw(first_approver)
        record.action_withdraw(second_approver)
        self.assertEqual(record.state, "pending")
        record.action_approve(first_approver)
        self.assertEqual(record.state, "pending")
        record.action_approve(second_approver)
        self.assertEqual(record.state, "approved")

    def test_copy_logs_source_and_resets_the_name(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0005",
                "name": "Smart Clone Cat",
                "approval_minimum": 1,
                "step_ids": pool_step([(self.approver_user_1.id, True, 10)], minimum=1),
            }
        )
        for amt in (100, 200):
            historical = self.env["approval.request"].create(
                {
                    "name": "Hist %s" % amt,
                    "request_owner_id": self.env.user.id,
                    "category_id": category.id,
                    "amount": amt,
                }
            )
            historical.action_confirm()
            record_approval(historical.approver_ids)
        source = self.env["approval.request"].create(
            {
                "name": "source",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "amount": 1000,
            }
        )

        duplicate = source.copy()

        self.assertFalse(duplicate.name)
        self.assertEqual(duplicate.display_name, self.env._("New"))
        body = " ".join(duplicate.message_ids.mapped("body"))
        self.assertIn("Duplicated from", body)
        self.assertIn(str(source.id), body)

    def test_unlink_approval(self):
        approval = self.env["approval.request"].create(
            {
                "name": "test request",
                "category_id": new_trip_category(self.env).id,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now(),
            }
        )
        self.env["ir.attachment"].create(
            {
                "name": "test.file",
                "res_id": approval.id,
                "res_model": "approval.request",
            }
        )

        self.env["ir.model.fields"].create(
            {
                "name": "x_test_field",
                "model_id": self.env.ref("approval.model_approval_request").id,
                "ttype": "binary",
            }
        )
        approval.x_test_field = "test"
        approval.unlink()

    def test_request_is_numbered_on_confirm(self):
        approval_category = self.env["approval.category"].create(
            {
                "name": "Test Category",
                "sequence_code": "1234",
            }
        )

        request_form = Form(self.env["approval.request"])
        request_form.category_id = approval_category
        approval_request = request_form.save()
        self.assertFalse(approval_request.name)
        self.assertEqual(approval_request.display_name, self.env._("New"))
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": approval_request.id,
                "flow_state": "new",
            }
        )
        approval_request.action_confirm()
        self.assertEqual(approval_request.name, "123400001")


@tagged("post_install", "-at_install")
class TestRequestAuditRegressions(ApprovalCommon):
    def test_c2_state_not_approved_below_configured_minimum(self):
        category = self._make_category(
            approval_minimum=3,
            approvers=[
                (self.approver_1, False, 10),
                (self.approver_2, False, 20),
            ],
        )
        request = self._prepare_request(category, confirm=False)

        with self.assertRaises(
            UserError,
            msg="action_confirm should refuse a request with fewer "
            "approvers than approval_minimum.",
        ):
            request.action_confirm()

        request.approver_ids.sudo().write({"flow_state": "pending"})
        record_approval(request.approver_ids)
        request.invalidate_recordset(["state"])
        self.assertNotEqual(
            request.state,
            "approved",
            "_compute_state approved a request with only 2 of 3 required approvals.",
        )

    def test_h3_confirm_rejects_non_draft_state(self):
        category = self._make_category(
            approval_minimum=2,
            in_order=True,
            approvers=[self.approver_1, self.approver_2],
        )
        request = self._prepare_request(category)
        self.assertEqual(request.state, "pending")

        with self.assertRaises(
            UserError,
            msg="action_confirm should refuse to run on a request "
            "already in 'pending' state.",
        ):
            request.action_confirm()

    def test_create_activity_is_idempotent(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)
        approver = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        self.assertTrue(approver)

        activity_type = self.env.ref("approval.mail_activity_data_approval")
        initial = request.activity_ids.filtered(
            lambda a: (
                a.activity_type_id == activity_type and a.user_id == self.approver_1
            ),
        )
        self.assertEqual(
            len(initial),
            1,
            "action_confirm should have scheduled exactly one activity.",
        )

        approver._create_activity()
        request.invalidate_recordset(["activity_ids"])

        after = request.activity_ids.filtered(
            lambda a: (
                a.activity_type_id == activity_type and a.user_id == self.approver_1
            ),
        )
        self.assertEqual(
            len(after),
            1,
            "Duplicate _create_activity call must NOT schedule a second activity.",
        )


@tagged("post_install", "-at_install")
class TestWithdrawCloseOut(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_3 = cls.env["res.users"].create(
            {
                "name": "Approver Three",
                "login": "withdraw_closeout_approver_3",
                "email": "approver3.closeout@test.com",
                "group_ids": [
                    (4, cls.env.ref("approval.group_approval_approver").id),
                ],
            },
        )

    def _approval_todos(self, request, user):
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        return request.activity_ids.filtered(
            lambda a: a.activity_type_id == activity_type and a.user_id == user,
        )

    def _over_approved_request(self, extra_approvers=()):
        approvers = [(self.approver_1, True, 10), (self.approver_2, False, 20)]
        approvers.extend(extra_approvers)
        category = self._make_category(
            name=f"Close-out Cat {self.id()}",
            approval_minimum=1,
            approvers=approvers,
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(
            request.state,
            "pending",
            "The minimum is met but the required approver has not decided.",
        )
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")
        return request

    def test_withdrawing_a_surplus_approval_parks_the_row(self):
        request = self._over_approved_request()
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)

        request.with_user(self.approver_2).action_withdraw()

        self.assertEqual(
            request.state,
            "approved",
            "One approval short of nothing: the remaining approval still "
            "satisfies the minimum AND the required row.",
        )
        self.assertEqual(
            row.state,
            "waiting",
            "A row left 'pending' on an approved request is a To-Do whose "
            "Approve button raises — the ghost inbox _apply_decision's "
            "close-out exists to prevent.",
        )
        self.assertFalse(
            row.decision_date,
            "The withdrawal un-makes the decision, so it stops counting "
            "towards the approver-performance analytics.",
        )
        self.assertFalse(
            self._approval_todos(request, self.approver_2),
            "No To-Do may be scheduled for a decided request.",
        )

    def test_withdrawing_a_surplus_approval_leaves_parked_siblings_parked(self):
        request = self._over_approved_request(
            extra_approvers=[(self.approver_3, False, 30)],
        )
        sibling = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_3,
        )
        self.assertEqual(
            sibling.state,
            "waiting",
            "The third approver never acted and was parked when the "
            "minimum was reached.",
        )

        request.with_user(self.approver_2).action_withdraw()

        self.assertEqual(request.state, "approved")
        self.assertEqual(
            sibling.state,
            "waiting",
            "A withdrawal that does not reopen the request must not "
            "unpark the rows the approval closed out.",
        )
        self.assertFalse(self._approval_todos(request, self.approver_3))

    def test_withdrawing_the_decisive_approval_still_reopens(self):
        request = self._over_approved_request(
            extra_approvers=[(self.approver_3, False, 30)],
        )
        required_row = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        sibling = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_3,
        )

        request.with_user(self.approver_1).action_withdraw()

        self.assertEqual(
            request.state,
            "pending",
            "Withdrawing the REQUIRED approval breaks the approved "
            "condition, so the decision window reopens.",
        )
        self.assertEqual(required_row.state, "pending")
        self.assertTrue(self._approval_todos(request, self.approver_1))
        self.assertEqual(
            sibling.state,
            "pending",
            "Rows parked when the minimum was reached come back with the request.",
        )
        self.assertTrue(self._approval_todos(request, self.approver_3))

    def test_surplus_withdrawal_leaves_the_source_document_approved(self):
        request = self._over_approved_request()
        notified = []
        self.patch(
            type(request),
            "_notify_source_document_state_change",
            lambda self, new_state: notified.append(new_state),
        )

        request.with_user(self.approver_2).action_withdraw()

        self.assertEqual(
            notified,
            [],
            "The request never left 'approved'; the document has nothing to react to.",
        )


class TestMailActivitySearch(common.TransactionCase):
    def test_negative_operator_raises_error(self):
        with self.assertRaises(UserError) as ctx:
            self.env["mail.activity"].search([("approval_request_id", "!=", 1)])

        self.assertIn("not supported", str(ctx.exception).lower())
