from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import common, tagged

from .common import ApprovalCommon, add_category_approver, new_trip_category
from odoo.addons.approval.models import approval_request_escalation as cron_module


@tagged("post_install", "-at_install")
class TestAutoExpire(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Expire Approver",
                "login": "expire_approver",
                "email": "expire@test.com",
            }
        )
        cls.owner = cls.env.ref("base.user_admin")
        cls.category = new_trip_category(cls.env)
        cls.category.write(
            {
                "auto_expire_hours": 48,
            }
        )
        add_category_approver(
            cls.category, cls.approver_user, required=True, sequence=10
        )

    def _create_and_confirm(self, **kwargs):
        vals = {
            "name": "Expire Test",
            "category_id": self.category.id,
            "request_owner_id": self.owner.id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
        }
        vals.update(kwargs)
        request = self.env["approval.request"].create(vals)
        request.action_confirm()
        return request

    def test_expire_cancels_stale_requests(self):
        request = self._create_and_confirm()
        self.assertEqual(request.state, "pending")

        request.date_confirmed = fields.Datetime.now() - timedelta(hours=72)

        self.env["approval.request"].cron_auto_expire()
        self.assertEqual(request.state, "cancelled")
        self.assertTrue(request.date_cancelled)
        self.assertFalse(request.date_refused)
        self.assertFalse(request.refusal_reason_id)

    def test_expire_cancels_a_request_awaiting_a_requested_change(self):
        request = self._create_and_confirm()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user,
        )
        request.with_user(self.approver_user).with_context(
            skip_wizard=True,
            requested_change_field="reason",
        ).action_request_change(approver=approver)
        self.assertEqual(request.pending_change_field, "reason")

        request.date_confirmed = fields.Datetime.now() - timedelta(hours=72)
        self.env["approval.request"].cron_auto_expire()

        self.assertEqual(request.state, "cancelled")
        self.assertTrue(
            all(a.state == "cancelled" for a in request.approver_ids),
        )

    def test_expire_ignores_fresh_requests(self):
        request = self._create_and_confirm()
        self.assertEqual(request.state, "pending")

        self.env["approval.request"].cron_auto_expire()
        self.assertEqual(request.state, "pending")

    def test_expire_ignores_disabled_categories(self):
        self.category.auto_expire_hours = 0
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=72)

        self.env["approval.request"].cron_auto_expire()
        self.assertEqual(request.state, "pending")

    def test_expire_ignores_non_pending(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=72)

        request.with_user(self.approver_user).action_approve()
        self.assertEqual(request.state, "approved")

        self.env["approval.request"].cron_auto_expire()
        self.assertEqual(request.state, "approved")

    def test_expire_posts_notification(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=72)
        msg_count_before = len(request.message_ids)

        self.env["approval.request"].cron_auto_expire()

        self.assertGreater(len(request.message_ids), msg_count_before)


@tagged("post_install", "-at_install")
class TestCronBatchLimitIsPerTick(ApprovalCommon):
    def _expired_request(self, category, hours_ago):
        request = self._prepare_request(category)
        request.sudo().write(
            {"date_confirmed": fields.Datetime.now() - timedelta(hours=hours_ago)},
        )
        return request

    def test_auto_expire_caps_the_whole_tick(self):
        categories = [
            self._make_category(
                name=f"Expiring {i}", approvers=[self.approver_1], auto_expire_hours=1
            )
            for i in range(3)
        ]
        for category in categories:
            for _ in range(2):
                self._expired_request(category, hours_ago=5)
        self.env.flush_all()

        with patch.object(cron_module, "CRON_BATCH_LIMIT", 1):
            self.env["approval.request"].cron_auto_expire()
        self.env.flush_all()

        cancelled = self.env["approval.request"].search_count(
            [
                ("category_id", "in", [c.id for c in categories]),
                ("state", "=", "cancelled"),
            ],
        )
        self.assertEqual(
            cancelled,
            1,
            "With the batch limit at 1, a single tick must cancel one "
            "request in total — not one per category.",
        )

    def test_auto_expire_drains_oldest_first_across_categories(self):
        cat_a = self._make_category(
            name="Expiring A", approvers=[self.approver_1], auto_expire_hours=1
        )
        cat_b = self._make_category(
            name="Expiring B", approvers=[self.approver_1], auto_expire_hours=1
        )
        newer = self._expired_request(cat_a, hours_ago=3)
        oldest = self._expired_request(cat_b, hours_ago=50)
        self.env.flush_all()

        with patch.object(cron_module, "CRON_BATCH_LIMIT", 1):
            self.env["approval.request"].cron_auto_expire()
        self.env.flush_all()

        self.assertEqual(oldest.state, "cancelled")
        self.assertEqual(
            newer.state,
            "pending",
            "The one available slot must go to the oldest request overall.",
        )

    def test_auto_expire_still_reports_each_category_own_window(self):
        fast = self._make_category(
            name="Fast Expiry", approvers=[self.approver_1], auto_expire_hours=2
        )
        slow = self._make_category(
            name="Slow Expiry", approvers=[self.approver_1], auto_expire_hours=24
        )
        fast_request = self._expired_request(fast, hours_ago=100)
        slow_request = self._expired_request(slow, hours_ago=100)
        self.env.flush_all()

        self.env["approval.request"].cron_auto_expire()
        self.env.flush_all()

        self.assertEqual(fast_request.state, "cancelled")
        self.assertEqual(slow_request.state, "cancelled")
        self.assertTrue(
            any("2-hour" in str(m.body) for m in fast_request.message_ids),
            "The fast category's message must quote its own 2-hour window.",
        )
        self.assertTrue(
            any("24-hour" in str(m.body) for m in slow_request.message_ids),
            "The slow category's message must quote its own 24-hour window.",
        )

    def test_auto_expire_respects_each_category_threshold(self):
        slow = self._make_category(
            name="Slow Only", approvers=[self.approver_1], auto_expire_hours=48
        )
        self._make_category(
            name="Fast Peer", approvers=[self.approver_1], auto_expire_hours=1
        )
        young = self._expired_request(slow, hours_ago=5)
        self.env.flush_all()

        self.env["approval.request"].cron_auto_expire()
        self.env.flush_all()

        self.assertEqual(
            young.state,
            "pending",
            "A request 5h old in a 48h-window category must survive, even "
            "though a peer category expires at 1h.",
        )
