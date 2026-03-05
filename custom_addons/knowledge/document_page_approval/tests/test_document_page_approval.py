from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestDocumentPageApproval(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page_obj = cls.env["document.page"]
        cls.history_obj = cls.env["document.page.history"]

        # Demo Data
        cls.category1 = cls.env.ref("document_page.demo_category1")
        cls.page1 = cls.env.ref("document_page.demo_page1")

        # Create test user without groups first
        cls.user2 = new_test_user(
            cls.env,
            login="test-user2",
            groups="document_page_approval.group_document_approver_user",
        )

        # Ensure user2 has the approver group
        cls.approver_gid = cls.env.ref(
            "document_page_approval.group_document_approver_user"
        )
        cls.user2.write({"group_ids": [Command.link(cls.approver_gid.id)]})

        # Create category and page that require approval
        cls.category2 = cls.page_obj.create(
            {
                "name": "This category requires approval",
                "type": "category",
                "approval_required": True,
                "approver_gid": cls.approver_gid.id,
            }
        )
        cls.page2 = cls.page_obj.create(
            {
                "name": "This page requires approval",
                "parent_id": cls.category2.id,
                "content": "<p>This content will require approval</p>",
            }
        )

    def test_approval_required(self):
        """Test that the page requires approval."""
        page = self.page2
        self.assertTrue(page.is_approval_required)
        self.assertTrue(page.has_changes_pending_approval)
        self.assertEqual(len(page.history_ids), 0)

    def test_change_request_approve(self):
        """Test that an approver can approve a change request."""
        page = self.page2

        # Get the change request for this page
        chreq = self.history_obj.search(
            [("page_id", "=", page.id), ("state", "!=", "approved")], limit=1
        )

        self.assertEqual(chreq.state, "to approve")

        # Ensure user2 is listed as an approver
        self.assertTrue(chreq.with_user(self.user2).am_i_approver)

        # Approve the request as user2 (approver)
        chreq.with_user(self.user2).action_approve()
        self.assertEqual(chreq.state, "approved")
        self.assertEqual(chreq.content, page.content)

        # Create new change request
        page.write({"content": "<p>New content</p>"})
        page.invalidate_model()  # Recompute fields
        chreq = self.history_obj.search(
            [("page_id", "=", page.id), ("state", "!=", "approved")], limit=1
        )

        # Approve new changes
        chreq.with_user(self.user2).action_approve()
        self.assertEqual(page.content, "<p>New content</p>")

    def test_change_request_auto_approve(self):
        """Test that a page without approval required auto-approves changes."""
        page = self.page1
        self.assertFalse(page.is_approval_required)
        page.write({"content": "<p>New content</p>"})
        self.assertEqual(page.content, "<p>New content</p>")

    def test_change_request_from_scratch(self):
        """Test a full change request lifecycle from draft to approval."""
        page = self.page2

        # Approve all pending change requests
        self.history_obj.search(
            [("page_id", "=", page.id), ("state", "!=", "approved")]
        ).with_user(self.user2).action_approve()

        # Create new change request
        chreq = self.history_obj.create(
            {
                "page_id": page.id,
                "summary": "Changed something",
                "content": "<p>New content</p>",
            }
        )

        self.assertEqual(chreq.state, "draft")
        chreq.action_to_approve()
        self.assertEqual(chreq.state, "to approve")

        # Cancel and return to draft
        chreq.with_user(self.user2).action_cancel()
        self.assertEqual(chreq.state, "cancelled")

        chreq.with_user(self.user2).action_draft()
        self.assertEqual(chreq.state, "draft")

        chreq.action_to_approve()
        self.assertEqual(chreq.state, "to approve")
        chreq.with_user(self.user2).action_approve()
        self.assertEqual(chreq.state, "approved")
        self.assertEqual(page.content, chreq.content)
        self.assertEqual(page.approved_date, chreq.approved_date)
        self.assertEqual(page.approved_uid, chreq.approved_uid)

    def test_get_approvers_guids(self):
        """Test that approver groups are properly assigned."""
        page = self.page2
        self.assertTrue(len(page.approver_group_ids) > 0)

    def test_get_page_url(self):
        """Test that the page URL exists."""
        pages = self.env["document.page.history"].search([])
        page = pages[0]
        self.assertIsNotNone(page.page_url)

    def test_compute_is_approval_required(self):
        """Ensure approval rules are inherited correctly"""
        self.assertTrue(self.page2.is_approval_required)
        self.page2.parent_id.approval_required = False
        self.page2.invalidate_model()
        self.assertFalse(self.page2.is_approval_required)

    def test_compute_approver_group_ids(self):
        """Ensure approver groups are inherited correctly"""
        self.assertIn(self.approver_gid, self.page2.approver_group_ids)
        self.page2.parent_id.approver_gid = False
        self.page2.invalidate_model()
        self.assertFalse(self.page2.approver_group_ids)

    def test_can_user_approve_this_page(self):
        """Check different approval conditions"""
        self.assertTrue(
            self.page2.with_user(self.user2).can_user_approve_this_page(self.user2)
        )

        # Remove approval group from user2
        self.user2.write({"group_ids": [(3, self.approver_gid.id)]})
        self.assertFalse(
            self.page2.with_user(self.user2).can_user_approve_this_page(self.user2)
        )

    def test_pending_approval_detection(self):
        """Ensure the system detects pending approval changes"""
        # Reset page2 by removing previous history
        self.history_obj.search([("page_id", "=", self.page2.id)]).unlink()

        self.page2.invalidate_model()
        self.assertFalse(self.page2.has_changes_pending_approval)

        # Create a new change request
        self.history_obj.create(
            {
                "page_id": self.page2.id,
                "state": "to approve",
            }
        )

        self.page2.invalidate_model()
        self.assertTrue(self.page2.has_changes_pending_approval)

    def test_user_has_drafts(self):
        """Ensure the system detects drafts correctly"""
        self.page2.invalidate_model()
        self.assertFalse(self.page2.user_has_drafts)

        self.history_obj.create(
            {
                "page_id": self.page2.id,
                "state": "draft",
            }
        )
        self.page2.invalidate_model()
        self.assertTrue(self.page2.user_has_drafts)

    def test_action_draft_requires_cancellation(self):
        """Ensure a change request must be cancelled before setting to draft"""
        chreq = self.history_obj.create(
            {
                "page_id": self.page2.id,
                "state": "to approve",
            }
        )
        with self.assertRaises(UserError):
            chreq.action_draft()

    def test_action_to_approve_only_from_draft(self):
        """Ensure only draft requests can be sent for approval"""
        chreq = self.history_obj.create(
            {
                "page_id": self.page2.id,
                "state": "approved",
            }
        )
        with self.assertRaises(UserError):
            chreq.action_to_approve()

    def test_approval_permission_check(self):
        """Ensure approval is restricted to approvers"""
        chreq = self.history_obj.create(
            {
                "page_id": self.page2.id,
                "state": "to approve",
            }
        )

        with self.assertRaises(UserError):
            chreq.with_user(self.env.ref("base.user_demo")).action_approve()

        # Grant approval rights
        chreq.with_user(self.user2).action_approve()
        self.assertEqual(chreq.state, "approved")

    def test_page_url_computation(self):
        """Ensure page URLs are generated correctly"""
        chreq = self.history_obj.create({"page_id": self.page2.id})
        self.assertIn("web#db=", chreq.page_url)

    def test_diff_computation(self):
        """Ensure document diff is calculated properly"""
        self.history_obj.create(
            {
                "page_id": self.page2.id,
                "content": "<p>Version 1</p>",
                "state": "approved",
            }
        )

        chreq2 = self.history_obj.create(
            {
                "page_id": self.page2.id,
                "content": "<p>Version 2</p>",
            }
        )
        chreq2._compute_diff()
        self.assertIsNotNone(chreq2.diff)
