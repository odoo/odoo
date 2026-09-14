from odoo.fields import Command
from odoo.tests import tagged

from .common import ApprovalCommon, pool_step


@tagged("post_install", "-at_install")
class TestPoolQueue(ApprovalCommon):
    """A security group is a pool any member may decide from, not a to-do per
    member."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env["res.groups"].create(
            {
                "name": "Pool",
                "user_ids": [Command.set((cls.approver_1 | cls.approver_2).ids)],
            }
        )

    def _pool_request(self, **step_vals):
        category = self.env["approval.category"].create(
            {
                "name": "Pool Category",
                "sequence_code": self._next_sequence_code(),
                "approval_minimum": 1,
                "step_ids": pool_step(
                    [], minimum=1, group_id=self.group.id, **step_vals
                ),
            }
        )
        return self._prepare_request(category)

    def _activities(self, request):
        return self.env["mail.activity"].search(
            [("approver_id", "in", request.approver_ids.ids)]
        )

    def test_a_pool_asks_nobody_individually(self):
        request = self._pool_request()
        self.assertEqual(
            request.approver_ids.user_id, self.approver_1 | self.approver_2
        )
        self.assertFalse(self._activities(request))

    def test_any_member_still_decides_from_the_queue(self):
        request = self._pool_request()
        self.assertTrue(request.with_user(self.approver_2).is_pending_my_review)
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")

    def test_a_category_may_still_ask_every_member(self):
        request = self._pool_request(asks_group_members=True)
        self.assertEqual(
            self._activities(request).user_id, self.approver_1 | self.approver_2
        )
