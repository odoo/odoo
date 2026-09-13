from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from .common import record_approval


@tagged("post_install", "-at_install")
class TestGroupApproval(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin_user = cls.env.ref("base.user_admin")
        cls.user1 = cls.env["res.users"].create(
            {
                "name": "Group Member 1",
                "login": "grp_member1",
                "email": "grp_member1@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.user2 = cls.env["res.users"].create(
            {
                "name": "Group Member 2",
                "login": "grp_member2",
                "email": "grp_member2@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.category_approver_user = cls.env["res.users"].create(
            {
                "name": "Category Approver",
                "login": "grp_category_approver",
                "email": "grp_cat_approver@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.approval_group = cls.env["res.groups"].create(
            {
                "name": "Test Approval Group",
                "user_ids": [(6, 0, [cls.user1.id, cls.user2.id])],
            }
        )

        cls.empty_group = cls.env["res.groups"].create(
            {
                "name": "Empty Approval Group",
                "user_ids": [(6, 0, [])],
            }
        )

    def test_group_approval_exclusive_mode_bypasses_category_approvers(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0043",
                "name": "Test Exclusive Group Approval",
                "approval_minimum": 1,
                "group_approval": "exclusive",
                "approver_group_id": self.approval_group.id,
            }
        )

        self.env["approval.category.approver"].create(
            {
                "user_id": self.category_approver_user.id,
                "category_id": category.id,
                "required": True,
            }
        )

        request = self.env["approval.request"].create(
            {
                "name": "Test Exclusive Mode",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        approver_user_ids = request.approver_ids.mapped("user_id").ids

        self.assertIn(self.user1.id, approver_user_ids)
        self.assertIn(self.user2.id, approver_user_ids)
        self.assertNotIn(
            self.category_approver_user.id,
            approver_user_ids,
            "Explicit approver must NOT appear in exclusive mode",
        )
        self.assertEqual(
            len(approver_user_ids),
            2,
            "Should have exactly the 2 group members",
        )

    def test_approver_group_user_ids_mirrors_all_user_ids(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0045",
                "name": "Test Group Members Display",
                "approval_minimum": 1,
                "group_approval": "exclusive",
                "approver_group_id": self.approval_group.id,
            }
        )

        self.assertEqual(
            category.approver_group_user_ids,
            self.approval_group.all_user_ids,
            "Group Members must mirror approver_group_id.all_user_ids",
        )
        self.assertEqual(
            set(category.approver_group_user_ids.ids),
            {self.user1.id, self.user2.id},
        )

        other_group = self.env["res.groups"].create(
            {
                "name": "Other Approval Group",
                "user_ids": [(6, 0, [self.category_approver_user.id])],
            }
        )
        category.approver_group_id = other_group
        self.assertEqual(
            category.approver_group_user_ids,
            other_group.all_user_ids,
        )
        self.assertEqual(
            category.approver_group_user_ids.ids,
            [self.category_approver_user.id],
        )

    def test_approver_group_user_ids_empty_without_group(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0046",
                "name": "Test No Group Members",
                "approval_minimum": 1,
                "group_approval": "no",
            }
        )
        self.assertFalse(category.approver_group_user_ids)

    def test_group_approval_empty_group_exclusive_mode_raises_error(self):
        with self.assertRaises(ValidationError):
            self.env["approval.category"].create(
                {
                    "sequence_code": "SC0047",
                    "name": "Test Empty Group Validation",
                    "approval_minimum": 1,
                    "group_approval": "exclusive",
                    "approver_group_id": self.empty_group.id,
                }
            )

    def test_group_approval_no_group_selected_raises_error(self):
        with self.assertRaises(ValidationError):
            self.env["approval.category"].create(
                {
                    "sequence_code": "SC0048",
                    "name": "Test No Group Validation",
                    "approval_minimum": 1,
                    "group_approval": "exclusive",
                }
            )

    def test_group_approval_no_mode_does_not_add_group_members(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0049",
                "name": "Test No Group Approval",
                "approval_minimum": 1,
                "group_approval": "no",
                "approver_group_id": self.approval_group.id,
            }
        )

        self.env["approval.category.approver"].create(
            {
                "user_id": self.category_approver_user.id,
                "category_id": category.id,
                "required": True,
            }
        )

        request = self.env["approval.request"].create(
            {
                "name": "Test No Group Mode",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        approver_user_ids = request.approver_ids.mapped("user_id").ids
        self.assertIn(self.category_approver_user.id, approver_user_ids)
        self.assertNotIn(self.user1.id, approver_user_ids)
        self.assertNotIn(self.user2.id, approver_user_ids)
        self.assertEqual(len(approver_user_ids), 1)

    def test_group_approval_exclusive_mode_with_minimum_approval(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0050",
                "name": "Test Exclusive with Minimum",
                "approval_minimum": 2,
                "group_approval": "exclusive",
                "approver_group_id": self.approval_group.id,
            }
        )

        request = self.env["approval.request"].create(
            {
                "name": "Test Minimum with Exclusive",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        request.action_confirm()

        approver1 = request.approver_ids.filtered(lambda a: a.user_id == self.user1)
        record_approval(approver1)
        self.assertEqual(
            request.state,
            "pending",
            "Request should be pending after 1 approval (minimum is 2)",
        )

        approver2 = request.approver_ids.filtered(lambda a: a.user_id == self.user2)
        record_approval(approver2)
        self.assertEqual(
            request.state,
            "approved",
            "Request should be approved after 2 approvals (minimum met)",
        )

    def test_group_approval_only_asks_the_members_who_work_in_the_company(self):
        other_company = self.env["res.company"].create({"name": "Elsewhere Co"})
        elsewhere_only = self.env["res.users"].create(
            {
                "name": "Elsewhere Member",
                "login": "grp_member_elsewhere",
                "email": "grp_member_elsewhere@test.com",
                "company_id": other_company.id,
                "company_ids": [(6, 0, [other_company.id])],
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.approval_group.user_ids = [(4, elsewhere_only.id)]
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0051",
                "name": "Test Group Across Companies",
                "company_id": False,
                "approval_minimum": 1,
                "group_approval": "exclusive",
                "approver_group_id": self.approval_group.id,
            }
        )

        request = self.env["approval.request"].create(
            {
                "name": "Raised in the current company",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        self.assertEqual(request.company_id, self.env.company)
        self.assertEqual(request.approver_ids.user_id, self.user1 | self.user2)
