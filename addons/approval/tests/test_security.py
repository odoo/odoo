from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, tagged

from .common import ApprovalCommon, add_category_approver, add_rule_step


@tagged("post_install", "-at_install")
class TestApproverAccessControl(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin_user = cls.env.ref("base.user_admin")

        cls.user_1 = cls.env["res.users"].create(
            {
                "name": "Test User 1",
                "login": "test_user_sec_1",
                "email": "user_sec_1@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.user_2 = cls.env["res.users"].create(
            {
                "name": "Test User 2",
                "login": "test_user_sec_2",
                "email": "user_sec_2@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.user_3 = cls.env["res.users"].create(
            {
                "name": "Test User 3",
                "login": "test_user_sec_3",
                "email": "user_sec_3@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0052",
                "name": "Security Test Category",
                "approval_minimum": 1,
            }
        )

        add_category_approver(cls.category, cls.user_2, required=True)

    def _create_pending_request(self, owner):
        request = self.env["approval.request"].create(
            {
                "name": "Security Test Request",
                "request_owner_id": owner.id,
                "category_id": self.category.id,
            }
        )
        request.action_confirm()
        return request

    def test_regular_user_cannot_create_approver(self):
        request = self._create_pending_request(self.user_1)

        with self.assertRaises(AccessError):
            self.env["approval.approver"].with_user(self.user_3).create(
                {
                    "user_id": self.user_3.id,
                    "request_id": request.id,
                    "flow_state": "pending",
                }
            )

    def test_regular_user_cannot_remove_approver(self):
        request = self._create_pending_request(self.user_1)
        approver = request.approver_ids[0]

        approver.sudo().write({"flow_state": "new"})

        with self.assertRaises(AccessError):
            approver.with_user(self.user_3).unlink()

    def test_approver_can_only_modify_own_record(self):
        request = self._create_pending_request(self.user_1)
        approver = request.approver_ids.filtered(lambda a: a.user_id == self.user_2)

        with self.assertRaises(AccessError):
            approver.with_user(self.user_3).write({"note": "Hijacked!"})

    def test_owner_cannot_approve_own_request(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0053",
                "name": "Self Approval Test",
                "approval_minimum": 1,
            }
        )
        add_category_approver(category, self.user_1)

        request = (
            self.env["approval.request"]
            .with_user(self.user_1)
            .create(
                {
                    "name": "Self Approval Request",
                    "request_owner_id": self.user_1.id,
                    "category_id": category.id,
                }
            )
        )

        with self.assertRaises(UserError, msg="the owner is the only approver"):
            request.action_confirm()
        self.assertFalse(
            request.approver_ids.filtered(lambda a: a.user_id == self.user_1),
            "the owner is never staged as an approver of their own request",
        )

    def test_owner_may_approve_own_request_where_the_category_allows_it(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0054",
                "name": "Self Approval Allowed",
                "approval_minimum": 1,
                "allow_self_approval": True,
            }
        )
        add_category_approver(category, self.user_1)
        request = (
            self.env["approval.request"]
            .with_user(self.user_1)
            .create({"request_owner_id": self.user_1.id, "category_id": category.id})
        )
        request.action_confirm()
        request.approver_ids.with_user(self.user_1).with_context(
            skip_wizard=True
        ).action_approve()
        self.assertEqual(request.state, "approved")

    def test_owner_cannot_decide_their_row_once_the_policy_forbids_it(self):
        """The policy is read when deciding, not only when routing, and under
        sudo too: a row staged while the category allowed self-approval cannot
        carry the owner's decision after it stops allowing it."""
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0055",
                "name": "Policy tightened",
                "approval_minimum": 1,
                "allow_self_approval": True,
            }
        )
        add_category_approver(category, self.user_1)
        request = (
            self.env["approval.request"]
            .with_user(self.user_1)
            .create({"request_owner_id": self.user_1.id, "category_id": category.id})
        )
        request.action_confirm()
        category.allow_self_approval = False
        own_row = request.approver_ids.filtered(lambda a: a.user_id == self.user_1)
        self.assertTrue(own_row)
        with self.assertRaises(AccessError):
            request.with_user(self.user_1).sudo().action_approve(own_row)
        self.assertEqual(request.state, "pending")


@tagged("post_install", "-at_install")
class TestBusinessRuleEnforcement(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin_user = cls.env.ref("base.user_admin")
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Approver Business Rules",
                "login": "approver_br",
                "email": "approver_br@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0054",
                "name": "Business Rules Category",
                "approval_minimum": 1,
            }
        )

        add_category_approver(cls.category, cls.approver_user, required=True)

    def test_cannot_add_approver_to_pending_request(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Pending Add Approver",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        request.action_confirm()
        self.assertEqual(request.state, "pending")

        with self.assertRaises(ValidationError):
            self.env["approval.approver"].sudo().create(
                {
                    "user_id": self.admin_user.id,
                    "request_id": request.id,
                    "flow_state": "pending",
                }
            )

    def test_cannot_remove_approver_from_pending_request(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Pending Remove Approver",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        request.action_confirm()
        approver = request.approver_ids[0]

        with self.assertRaises(ValidationError):
            approver.sudo().unlink()

    def test_minimum_approvals_enforced(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0055",
                "name": "Min 2 Approvals",
                "approval_minimum": 2,
            }
        )

        add_category_approver(category, self.approver_user)

        request = self.env["approval.request"].create(
            {
                "name": "Test Min Approvals",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        with self.assertRaises(UserError):
            request.action_confirm()

    def _prepare_request(self, state):
        request = self.env["approval.request"].create(
            {
                "name": "Unlink Guard %s" % state,
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        if state == "new":
            return request
        request.action_confirm()
        if state == "pending":
            return request
        approver = request.approver_ids[:1]
        if state == "approved":
            approver.with_context(skip_wizard=True).action_approve()
        elif state == "refused":
            approver.with_context(skip_wizard=True).action_refuse()
        return request

    def test_unlink_blocked_in_pending(self):
        request = self._prepare_request("pending")
        with self.assertRaises(ValidationError):
            request.with_user(self.admin_user).unlink()

    def test_unlink_blocked_in_approved(self):
        manager_group = self.env.ref("approval.group_approval_manager")
        manager = self.env["res.users"].create(
            {
                "name": "Approval Manager",
                "login": "approval_manager_t21613",
                "email": "mgr_t21613@test.com",
                "group_ids": [(6, 0, [manager_group.id])],
            }
        )
        request = self._prepare_request("approved")
        with self.assertRaises(ValidationError):
            request.with_user(manager).unlink()

    def test_unlink_blocked_in_cancel_as_manager(self):
        manager_group = self.env.ref("approval.group_approval_manager")
        manager = self.env["res.users"].create(
            {
                "name": "Approval Manager Cancel",
                "login": "approval_manager_cancel_t21613",
                "email": "mgr_cancel_t21613@test.com",
                "group_ids": [(6, 0, [manager_group.id])],
            }
        )
        request = self._prepare_request("refused")
        with self.assertRaises(ValidationError):
            request.with_user(manager).unlink()

    def test_unlink_allowed_in_new_as_owner(self):
        request = self._prepare_request("new")
        request_id = request.id
        request.with_user(self.admin_user).unlink()
        self.assertFalse(
            self.env["approval.request"].browse(request_id).exists(),
            "Draft request should be deletable by owner.",
        )

    def test_unlink_allowed_in_new_as_manager(self):
        manager_group = self.env.ref("approval.group_approval_manager")
        manager = self.env["res.users"].create(
            {
                "name": "Approval Manager Draft",
                "login": "approval_manager_draft_t21613",
                "email": "mgr_draft_t21613@test.com",
                "group_ids": [(6, 0, [manager_group.id])],
            }
        )
        request = self._prepare_request("new")
        request_id = request.id
        request.with_user(manager).unlink()
        self.assertFalse(
            self.env["approval.request"].browse(request_id).exists(),
            "Draft request should be deletable by manager.",
        )


@tagged("post_install", "-at_install")
class TestRecordRuleVisibility(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin_user = cls.env.ref("base.user_admin")

        cls.user_owner = cls.env["res.users"].create(
            {
                "name": "Request Owner",
                "login": "request_owner_vis",
                "email": "owner_vis@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.user_approver = cls.env["res.users"].create(
            {
                "name": "Request Approver",
                "login": "request_approver_vis",
                "email": "approver_vis@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.user_other = cls.env["res.users"].create(
            {
                "name": "Other User",
                "login": "other_user_vis",
                "email": "other_vis@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0056",
                "name": "Visibility Test Category",
                "approval_minimum": 1,
                "privacy_visibility": "private",
            }
        )

        add_category_approver(cls.category, cls.user_approver)

    def test_owner_can_see_own_request(self):
        request = (
            self.env["approval.request"]
            .with_user(self.user_owner)
            .create(
                {
                    "name": "Owner Visibility Test",
                    "request_owner_id": self.user_owner.id,
                    "category_id": self.category.id,
                }
            )
        )

        found = (
            self.env["approval.request"]
            .with_user(self.user_owner)
            .search([("id", "=", request.id)])
        )
        self.assertEqual(len(found), 1)

    def test_approver_can_see_request_to_approve(self):
        request = self.env["approval.request"].create(
            {
                "name": "Approver Visibility Test",
                "request_owner_id": self.user_owner.id,
                "category_id": self.category.id,
            }
        )
        request.action_confirm()

        found = (
            self.env["approval.request"]
            .with_user(self.user_approver)
            .search([("id", "=", request.id)])
        )
        self.assertEqual(len(found), 1)

    def test_unrelated_user_cannot_see_request(self):
        request = self.env["approval.request"].create(
            {
                "name": "Hidden Request Test",
                "request_owner_id": self.user_owner.id,
                "category_id": self.category.id,
            }
        )

        found = (
            self.env["approval.request"]
            .with_user(self.user_other)
            .search([("id", "=", request.id)])
        )
        self.assertEqual(len(found), 0, "Unrelated user should not see the request")


@tagged("post_install", "-at_install")
class TestManualApproverCreation(ApprovalCommon):
    def test_h9_regular_user_cannot_create_approver_manually(self):
        with self.assertRaises(
            AccessError,
            msg="regular user created an approver record by passing request_id=False.",
        ):
            self.env["approval.approver"].with_user(self.owner_user).create(
                {
                    "user_id": self.approver_2.id,
                    "sequence": 10,
                }
            )


@tagged("post_install", "-at_install")
class TestApproverDraftWriteAccess(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            name="Draft Write Cat",
            approvers=[(cls.approver_1, False, 10), (cls.approver_2, False, 20)],
        )

    def test_approver_cannot_write_a_draft_they_do_not_own(self):
        request = self._prepare_request(self.category, confirm=False, amount=100.0)

        with self.assertRaises(AccessError):
            request.with_user(self.approver_1).write({"amount": 999999.0})

        self.assertEqual(request.amount, 100.0)

    def test_owner_can_still_write_their_own_draft(self):
        request = self._prepare_request(self.category, confirm=False, amount=100.0)

        request.with_user(self.owner_user).write({"amount": 250.0})

        self.assertEqual(request.amount, 250.0)

    def test_approver_may_write_once_submitted_but_not_route(self):
        request = self._prepare_request(self.category, amount=100.0)

        with self.assertRaises(AccessError):
            request.with_user(self.approver_1).write({"priority": "3"})
        request.with_user(self.owner_user).write({"priority": "3"})
        self.assertEqual(request.priority, "3")

        with self.assertRaises(ValidationError):
            request.with_user(self.approver_1).write({"amount": 1.0})

    def test_approver_cannot_reroute_a_request_through_priority(self):
        add_rule_step(
            self.category,
            self.approver_2,
            name="urgent adds approver two",
            condition_field="priority",
            operator="gte",
            threshold=3,
        )
        category = self._make_category(name="Reroute", approvers=[self.approver_1])
        add_rule_step(
            category,
            self.approver_2,
            name="urgent adds approver two (reroute)",
            condition_field="priority",
            operator="gte",
            threshold=3,
        )
        request = self._prepare_request(category)
        self.assertEqual(request.approver_ids.user_id, self.approver_1)

        with self.assertRaises(AccessError):
            request.with_user(self.approver_1).write({"priority": "3"})
        self.assertEqual(request.approver_ids.user_id, self.approver_1)

        request.with_user(self.owner_user).write({"priority": "3"})
        self.assertIn(self.approver_2, request.approver_ids.user_id)

    def test_manager_cannot_decide_in_an_approvers_name(self):
        request = self._prepare_request(self.category)
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)

        with self.assertRaises(AccessError):
            row.with_user(self.manager_user).action_approve()
        with self.assertRaises(AccessError):
            request.with_user(self.manager_user).action_approve(row)
        with self.assertRaises(AccessError):
            request.with_user(self.manager_user).with_context(
                skip_wizard=True, requested_change_field="reason"
            ).action_request_change(approver=row)

        self.assertEqual(request.state, "pending")
        self.assertFalse(row.decided_by_user_id)

    def test_manager_is_unaffected(self):
        request = self._prepare_request(self.category, confirm=False, amount=100.0)

        request.with_user(self.manager_user).write({"amount": 500.0})

        self.assertEqual(request.amount, 500.0)


@tagged("post_install", "-at_install")
class TestVisibilityAudienceCoupling(ApprovalCommon):
    def test_naming_a_read_audience_also_restricts_creation(self):
        category = self._make_category("Audience Coupling")
        category.write(
            {
                "privacy_visibility": "restricted_users",
                "allowed_user_ids": [(6, 0, [self.approver_1.id])],
            },
        )

        self.env["approval.request"].with_user(self.approver_1).create(
            {"category_id": category.id, "request_owner_id": self.approver_1.id},
        )

        with self.assertRaises(
            ValidationError,
            msg="naming a read audience must also restrict who can create",
        ):
            self.env["approval.request"].with_user(self.owner_user).create(
                {"category_id": category.id, "request_owner_id": self.owner_user.id},
            )

    def test_empty_audience_lists_leave_creation_open(self):
        category = self._make_category("Audience Open")
        self.assertFalse(category.allowed_user_ids)
        self.assertFalse(category.allowed_group_ids)
        self.env["approval.request"].with_user(self.owner_user).create(
            {"category_id": category.id, "request_owner_id": self.owner_user.id},
        )
