from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, common, tagged

from .common import ApprovalCommon, new_trip_category


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
                "location": "testland",
            }
        )
        first_approver = self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": record.id,
                "state": "new",
            }
        )
        second_approver = self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_2.id,
                "request_id": record.id,
                "state": "new",
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
        self.env["approval.category.approver"].create(
            [
                {
                    "category_id": category_test.id,
                    "user_id": self.approver_user_1.id,
                    "required": True,
                    "sequence": 10,
                },
                {
                    "category_id": category_test.id,
                    "user_id": self.approver_user_2.id,
                    "required": False,
                    "sequence": 20,
                },
            ]
        )
        requester_user = self.env.ref("base.user_admin")
        record = self.env["approval.request"].create(
            {
                "name": "test request",
                "request_owner_id": requester_user.id,
                "category_id": category_test.id,
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now(),
                "location": "testland",
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

    def test_copy_uses_smart_defaults_and_logs_source(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0005",
                "name": "Smart Clone Cat",
                "has_amount": "required",
                "approval_minimum": 1,
                "approver_ids": [
                    Command.create(
                        {"user_id": self.approver_user_1.id, "required": True}
                    )
                ],
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
            historical.approver_ids.sudo().write({"state": "approved"})
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
        self.assertEqual(duplicate.amount, 150.0)
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
                "location": "testland",
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
                "state": "new",
            }
        )
        approval_request.action_confirm()
        self.assertEqual(approval_request.name, "123400001")

    def test_onchange_category_autofill_copies_required_fields(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0006",
                "name": "Test Autofill Category",
                "approval_minimum": 1,
                "has_location": "required",
                "has_partner": "required",
                "has_reference": "required",
            }
        )

        partner = self.env["res.partner"].create({"name": "Test Partner"})

        previous_request = self.env["approval.request"].create(
            {
                "name": "Previous Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Test Location",
                "partner_id": partner.id,
                "reference": "REF-123",
            }
        )

        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": previous_request.id,
            }
        )
        previous_request.action_confirm()
        previous_request.approver_ids.sudo().write({"state": "approved"})

        new_request = self.env["approval.request"].new(
            {
                "name": "New Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertEqual(
            new_request.location,
            "Test Location",
            "Location should be auto-filled from previous request",
        )
        self.assertEqual(
            new_request.partner_id,
            partner,
            "Partner should be auto-filled from previous request",
        )
        self.assertEqual(
            new_request.reference,
            "REF-123",
            "Reference should be auto-filled from previous request",
        )

    def test_onchange_category_autofill_skips_optional_fields(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0007",
                "name": "Test Optional Autofill",
                "approval_minimum": 1,
                "has_location": "optional",
                "has_partner": "required",
            }
        )

        partner = self.env["res.partner"].create({"name": "Test Partner"})

        previous_request = self.env["approval.request"].create(
            {
                "name": "Previous Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Should Not Copy",
                "partner_id": partner.id,
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": previous_request.id,
            }
        )
        previous_request.action_confirm()
        previous_request.approver_ids.sudo().write({"state": "approved"})

        new_request = self.env["approval.request"].new(
            {
                "name": "New Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertFalse(
            new_request.location,
            "Optional location should NOT be auto-filled",
        )
        self.assertEqual(
            new_request.partner_id,
            partner,
            "Required partner should be auto-filled",
        )

    def test_onchange_category_autofill_respects_existing_values(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0008",
                "name": "Test Respect Existing",
                "approval_minimum": 1,
                "has_location": "required",
            }
        )

        previous_request = self.env["approval.request"].create(
            {
                "name": "Previous Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Old Location",
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": previous_request.id,
            }
        )
        previous_request.action_confirm()
        previous_request.approver_ids.sudo().write({"state": "approved"})

        new_request = self.env["approval.request"].new(
            {
                "name": "New Request",
                "request_owner_id": self.env.user.id,
                "location": "My Custom Location",
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertEqual(
            new_request.location,
            "My Custom Location",
            "Existing location value should NOT be overwritten by autofill",
        )

    def test_onchange_category_autofill_no_previous_request(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0009",
                "name": "Test No Previous",
                "approval_minimum": 1,
                "has_location": "required",
            }
        )

        new_request = self.env["approval.request"].new(
            {
                "name": "First Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertFalse(
            new_request.location,
            "Location should be empty when no previous request",
        )

    def test_onchange_category_autofill_uses_most_recent_approved(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0010",
                "name": "Test Most Recent",
                "approval_minimum": 1,
                "has_location": "required",
            }
        )

        older_request = self.env["approval.request"].create(
            {
                "name": "Older Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Older Location",
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": older_request.id,
            }
        )
        older_request.action_confirm()
        older_request.approver_ids.sudo().write({"state": "approved"})
        older_request.sudo().write({"date_confirmed": "2025-01-01 10:00:00"})

        newer_request = self.env["approval.request"].create(
            {
                "name": "Newer Request",
                "request_owner_id": self.env.user.id,
                "category_id": category.id,
                "location": "Newer Location",
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_2.id,
                "request_id": newer_request.id,
            }
        )
        newer_request.action_confirm()
        newer_request.approver_ids.sudo().write({"state": "approved"})
        newer_request.sudo().write({"date_confirmed": "2025-10-01 10:00:00"})

        new_request = self.env["approval.request"].new(
            {
                "name": "Latest Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertEqual(
            new_request.location,
            "Newer Location",
            "Should use location from most recently approved request",
        )

    def test_onchange_category_autofill_only_current_user_requests(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0011",
                "name": "Test User Filtering",
                "approval_minimum": 1,
                "has_location": "required",
            }
        )

        other_user = self.env["res.users"].create(
            {
                "name": "Other User",
                "login": "other_user",
                "email": "other@test.com",
            }
        )

        other_user_request = self.env["approval.request"].create(
            {
                "name": "Other User Request",
                "request_owner_id": other_user.id,
                "category_id": category.id,
                "location": "Other User Location",
            }
        )
        self.env["approval.approver"].create(
            {
                "user_id": self.approver_user_1.id,
                "request_id": other_user_request.id,
            }
        )
        other_user_request.action_confirm()
        other_user_request.approver_ids.sudo().write({"state": "approved"})

        new_request = self.env["approval.request"].new(
            {
                "name": "Current User Request",
                "request_owner_id": self.env.user.id,
            }
        )

        new_request.category_id = category
        new_request._onchange_category_autofill()

        self.assertFalse(
            new_request.location,
            "Should NOT use other user's request data for autofill",
        )


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

        request.approver_ids.sudo().write({"state": "pending"})
        request.approver_ids.sudo().write({"state": "approved"})
        request.invalidate_recordset(["state"])
        self.assertNotEqual(
            request.state,
            "approved",
            "_compute_state approved a request with only 2 of 3 required approvals.",
        )

    def test_h3_confirm_rejects_non_draft_state(self):
        category = self._make_category(
            approval_minimum=2,
            approve_sequentially=True,
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


@tagged("post_install", "-at_install")
class TestSmartCloneUsesTheOwnersHistory(ApprovalCommon):
    def test_duplicating_anothers_request_seeds_from_that_owners_history(self):
        category = self._make_category("Clone Cat", approvers=[self.approver_1])
        category.write({"has_amount": "optional", "has_partner": "optional"})
        owner_partner = self.env["res.partner"].create({"name": "Owner Partner"})
        other_partner = self.env["res.partner"].create({"name": "Other Partner"})

        for _ in range(3):
            request = self._prepare_request(
                category,
                amount=1000.0,
                partner_id=owner_partner.id,
            )
            request.with_user(self.approver_1).action_approve()
        for _ in range(3):
            request = self._prepare_request(
                category,
                owner=self.manager_user,
                amount=7.0,
                partner_id=other_partner.id,
            )
            request.with_user(self.approver_1).action_approve()

        source = self._prepare_request(
            category,
            confirm=False,
            amount=1000.0,
            partner_id=owner_partner.id,
        )
        clone = source.with_user(self.manager_user).copy()

        self.assertEqual(clone.request_owner_id, self.owner_user)
        self.assertAlmostEqual(clone.amount, 1000.0, places=2)
        self.assertEqual(clone.partner_id, owner_partner)

    def test_the_history_lookup_is_bounded(self):
        category = self._make_category("Bounded Cat", approvers=[self.approver_1])
        for index in range(40):
            request = self._prepare_request(category, amount=100.0 + index)
            request.with_user(self.approver_1).action_approve()
        request = self._prepare_request(category, confirm=False)

        loaded = []
        Request = type(self.env["approval.request"])
        original = Request.search

        def spy(records, domain, *args, **kwargs):
            result = original(records, domain, *args, **kwargs)
            if "'approved'" in repr(domain):
                loaded.append(len(result))
            return result

        self.patch(Request, "search", spy)
        recent = request._recent_approved_by_owner(limit=10)

        self.assertEqual(len(recent), 10)
        self.assertTrue(loaded)
        self.assertLessEqual(
            loaded[0],
            10,
            "the lookup keeps 10 rows for one category but loaded %s" % loaded[0],
        )


class TestMailActivitySearch(common.TransactionCase):
    def test_negative_operator_raises_error(self):
        with self.assertRaises(UserError) as ctx:
            self.env["mail.activity"].search([("approval_request_id", "!=", 1)])

        self.assertIn("not supported", str(ctx.exception).lower())
