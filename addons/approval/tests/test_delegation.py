from ast import literal_eval
from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import common, tagged

from .common import ApprovalCommon, add_category_approver


@tagged("post_install", "-at_install")
class TestApprovalDelegation(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.admin_user = cls.env.ref("base.user_admin")
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Test Approver Delegation",
                "login": "test_approver_delegation",
                "email": "approver_delegation@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.delegate_user = cls.env["res.users"].create(
            {
                "name": "Test Delegate",
                "login": "test_delegate",
                "email": "delegate@test.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        cls.category = cls.env["approval.category"].create(
            {
                "sequence_code": "SC0039",
                "name": "Test Delegation Category",
                "approval_minimum": 1,
            }
        )

        add_category_approver(cls.category, cls.approver_user, required=True)

    def _create_pending_request(self):
        request = self.env["approval.request"].create(
            {
                "name": "Test Delegation Request",
                "request_owner_id": self.admin_user.id,
                "category_id": self.category.id,
            }
        )
        request.action_confirm()
        return request

    def test_delegation_dates_required_when_delegate_set(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        with self.assertRaises(ValidationError):
            approver.sudo().write(
                {
                    "delegate_id": self.delegate_user.id,
                }
            )

    def test_delegation_end_date_must_be_after_start(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        with self.assertRaises(ValidationError):
            approver.sudo().write(
                {
                    "delegate_id": self.delegate_user.id,
                    "delegate_start_date": today,
                    "delegate_end_date": today - timedelta(days=1),
                }
            )

    def test_delegation_same_day_allowed(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        approver.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today,
                "delegate_end_date": today,
            }
        )

        self.assertEqual(approver.delegate_id, self.delegate_user)

    def test_is_delegated_true_within_period(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        approver.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today - timedelta(days=1),
                "delegate_end_date": today + timedelta(days=1),
            }
        )

        self.assertTrue(
            approver.is_delegated,
            "is_delegated should be True when within delegation period",
        )

    def test_is_delegated_false_before_period(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        approver.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today + timedelta(days=1),
                "delegate_end_date": today + timedelta(days=7),
            }
        )

        self.assertFalse(
            approver.is_delegated,
            "is_delegated should be False before delegation period",
        )

    def test_is_delegated_false_after_period(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        approver.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today - timedelta(days=7),
                "delegate_end_date": today - timedelta(days=1),
            }
        )

        self.assertFalse(
            approver.is_delegated,
            "is_delegated should be False after delegation period",
        )

    def test_is_delegated_false_without_delegate(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        self.assertFalse(
            approver.is_delegated,
            "is_delegated should be False without delegate",
        )

    def test_effective_approver_is_delegate_when_delegated(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        approver.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today,
                "delegate_end_date": today + timedelta(days=7),
            }
        )

        effective = approver._get_effective_approver()
        self.assertEqual(
            effective,
            self.delegate_user,
            "Effective approver should be delegate when delegation is active",
        )

    def test_effective_approver_is_user_when_not_delegated(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        effective = approver._get_effective_approver()
        self.assertEqual(
            effective,
            self.approver_user,
            "Effective approver should be user_id when not delegated",
        )

    def test_effective_approver_is_user_when_delegation_expired(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        approver.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today - timedelta(days=7),
                "delegate_end_date": today - timedelta(days=1),
            }
        )

        effective = approver._get_effective_approver()
        self.assertEqual(
            effective,
            self.approver_user,
            "Effective approver should revert to user_id after delegation expires",
        )

    def test_delegate_wizard_sets_delegation(self):
        request = self._create_pending_request()

        today = fields.Date.today()
        start_date = today
        end_date = today + timedelta(days=7)

        wizard = (
            self.env["approval.delegate.wizard"]
            .with_user(self.approver_user)
            .create(
                {
                    "user_id": self.approver_user.id,
                    "delegate_id": self.delegate_user.id,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        )

        wizard.action_confirm()

        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        self.assertEqual(approver.delegate_id, self.delegate_user)
        self.assertEqual(approver.delegate_start_date, start_date)
        self.assertEqual(approver.delegate_end_date, end_date)

    def test_delegate_wizard_validates_date_range(self):
        today = fields.Date.today()

        with self.assertRaises(ValidationError):
            self.env["approval.delegate.wizard"].with_user(self.approver_user).create(
                {
                    "user_id": self.approver_user.id,
                    "delegate_id": self.delegate_user.id,
                    "start_date": today,
                    "end_date": today - timedelta(days=1),
                }
            )

    def test_delegate_wizard_cannot_delegate_to_self(self):
        today = fields.Date.today()

        with self.assertRaises(ValidationError):
            self.env["approval.delegate.wizard"].with_user(self.approver_user).create(
                {
                    "user_id": self.approver_user.id,
                    "delegate_id": self.approver_user.id,
                    "start_date": today,
                    "end_date": today + timedelta(days=7),
                }
            )

    def test_delegate_can_approve(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        approver.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today,
                "delegate_end_date": today + timedelta(days=7),
            }
        )

        approver.with_user(self.delegate_user).with_context(
            skip_wizard=True
        ).action_approve()

        self.assertEqual(approver.state, "approved")
        self.assertEqual(request.state, "approved")

    def test_original_approver_cannot_approve_when_delegated(self):
        request = self._create_pending_request()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )

        today = fields.Date.today()

        approver.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today,
                "delegate_end_date": today + timedelta(days=7),
            }
        )

        with self.assertRaises(AccessError):
            approver.with_user(self.approver_user).write({"state": "approved"})


@tagged("post_install", "-at_install")
class TestApprovalDelegationAuditRegressions(ApprovalCommon):
    def test_c1_delegation_activates_when_start_date_arrives(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        self.assertTrue(approver, "approver_1 must be on the request")

        today = fields.Date.today()
        start = today + timedelta(days=5)
        end = today + timedelta(days=10)

        approver.write(
            {
                "delegate_id": self.manager_user.id,
                "delegate_start_date": start,
                "delegate_end_date": end,
            }
        )
        self.assertFalse(
            approver.is_delegated,
            "Delegation should not be active before its start date.",
        )

        inside_window = start + timedelta(days=2)
        with patch.object(fields.Date, "context_today", return_value=inside_window):
            approver.invalidate_recordset(["is_delegated"])
            self.assertTrue(
                approver.is_delegated,
                "is_delegated did not activate when today reached delegate_start_date.",
            )
            self.assertEqual(
                approver._get_effective_approver(),
                self.manager_user,
                "Effective approver must flip to the delegate while the "
                "delegation window is active.",
            )

    def test_action_approve_fans_in_sibling_rows_sharing_one_delegate(self):
        category = self._make_category(
            approvers=[self.approver_1, self.approver_2],
            approval_minimum=2,
        )
        request = self._prepare_request(category)
        row_1 = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        row_2 = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_2,
        )
        today = fields.Date.context_today(self.env["approval.request"])
        delegation = {
            "delegate_id": self.manager_user.id,
            "delegate_start_date": today,
            "delegate_end_date": today,
        }
        row_1.write(delegation)
        row_2.write(delegation)
        self.assertEqual(row_1._get_effective_approver(), self.manager_user)
        self.assertEqual(row_2._get_effective_approver(), self.manager_user)

        row_1.with_user(self.manager_user).with_context(
            skip_wizard=True,
        ).action_approve()

        self.assertEqual(row_1.state, "approved")
        self.assertEqual(
            row_2.state,
            "approved",
            "The sibling row delegated to the same backup user must be "
            "approved too, not left pending with no visible activity.",
        )

    def _approval_activities(self, request, user):
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        return request.activity_ids.filtered(
            lambda a: a.user_id == user and a.activity_type_id == activity_type,
        )

    def test_redelegation_closes_prior_delegates_todo_not_originals(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)

        today = fields.Date.context_today(self.env["approval.request"])
        self.env["approval.delegate.wizard"].with_user(self.approver_1).create(
            {
                "user_id": self.approver_1.id,
                "delegate_id": self.approver_2.id,
                "start_date": today,
                "end_date": today,
            },
        ).action_confirm()
        self.assertFalse(self._approval_activities(request, self.approver_1))
        self.assertTrue(self._approval_activities(request, self.approver_2))

        self.env["approval.delegate.wizard"].with_user(self.approver_1).create(
            {
                "user_id": self.approver_1.id,
                "delegate_id": self.manager_user.id,
                "start_date": today,
                "end_date": today,
            },
        ).action_confirm()

        self.assertFalse(
            self._approval_activities(request, self.approver_2),
            "Re-delegating must close the PRIOR delegate's To-Do.",
        )
        self.assertEqual(
            len(self._approval_activities(request, self.manager_user)),
            1,
            "The new delegate must have exactly one To-Do.",
        )

    def test_redelegation_to_same_delegate_does_not_duplicate_activity(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)
        today = fields.Date.context_today(self.env["approval.request"])

        for _ in range(2):
            self.env["approval.delegate.wizard"].with_user(self.approver_1).create(
                {
                    "user_id": self.approver_1.id,
                    "delegate_id": self.approver_2.id,
                    "start_date": today,
                    "end_date": today,
                },
            ).action_confirm()

        self.assertEqual(
            len(self._approval_activities(request, self.approver_2)),
            1,
            "Re-running delegation to the same delegate must not "
            "duplicate their To-Do.",
        )


@tagged("post_install", "-at_install")
class TestDelegationTimezoneFrame(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.east = cls.env["res.users"].create(
            {
                "name": "East Approver",
                "login": "tz_east",
                "email": "tz.east@test.com",
                "tz": "Pacific/Kiritimati",
            },
        )
        cls.west = cls.env["res.users"].create(
            {
                "name": "West Delegate",
                "login": "tz_west",
                "email": "tz.west@test.com",
                "tz": "Pacific/Midway",
            },
        )
        cls.category = cls._make_category(
            name="TZ Delegation",
            approvers=[(cls.east, False, 10)],
        )

    def _delegated_request(self, start_offset, end_offset):
        request = self._prepare_request(self.category)
        row = request.approver_ids
        today = row._delegation_today()
        row.sudo().write(
            {
                "delegate_id": self.west.id,
                "delegate_start_date": today + timedelta(days=start_offset),
                "delegate_end_date": today + timedelta(days=end_offset),
            },
        )
        return request

    def _who_can_act(self, request):
        actors = set()
        for user in (self.east, self.west):
            scoped = request.with_user(user).with_context(tz=user.tz)
            scoped.invalidate_recordset()
            scoped.approver_ids.invalidate_recordset()
            if scoped._get_current_pending_approver():
                actors.add(user)
        return actors

    def test_exactly_one_actor_before_the_window_opens(self):
        request = self._delegated_request(1, 8)

        self.assertEqual(
            self._who_can_act(request),
            {self.east},
            "Before the window opens the original approver must still be "
            "able to act — previously neither of them could.",
        )

    def test_exactly_one_actor_on_the_window_last_day(self):
        request = self._delegated_request(-8, 0)

        self.assertEqual(
            self._who_can_act(request),
            {self.west},
            "While the window is open only the delegate may act — "
            "previously both could.",
        )

    def test_exactly_one_actor_after_the_window_closes(self):
        request = self._delegated_request(-9, -1)

        self.assertEqual(self._who_can_act(request), {self.east})

    def test_is_delegated_does_not_move_with_the_reader(self):
        request = self._delegated_request(1, 8)
        row = request.approver_ids

        answers = set()
        for tz in ("Pacific/Kiritimati", "Pacific/Midway", "UTC"):
            scoped = row.with_context(tz=tz)
            scoped.invalidate_recordset(["is_delegated"])
            answers.add(scoped.is_delegated)

        self.assertEqual(
            len(answers),
            1,
            "is_delegated is an authorization input; it must not depend "
            "on the timezone of whoever reads it.",
        )

    def test_search_matches_the_compute(self):
        rows = self.env["approval.approver"]
        for start, end in ((1, 8), (-8, 0), (-3, 3), (-9, -1)):
            rows |= self._delegated_request(start, end).approver_ids
        self.env.flush_all()

        active = rows.filtered("is_delegated")
        searched = self.env["approval.approver"].search(
            [("id", "in", rows.ids), ("is_delegated", "=", True)],
        )

        self.assertEqual(searched, active)
        self.assertEqual(
            self.env["approval.approver"].search(
                [("id", "in", rows.ids), ("is_delegated", "=", False)],
            ),
            rows - active,
        )


@tagged("post_install", "-at_install")
class TestPendingReviewSingleSource(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.delegate_user = cls.env["res.users"].create(
            {
                "name": "Backup Approver",
                "login": "inbox_delegate",
                "email": "inbox.delegate@test.com",
            },
        )
        cls.category = cls._make_category(
            name="Inbox Cat",
            approvers=[(cls.approver_1, False, 10)],
        )

    def setUp(self):
        super().setUp()
        self.request = self._prepare_request(self.category)
        today = fields.Date.today()
        self.request.approver_ids.sudo().write(
            {
                "delegate_id": self.delegate_user.id,
                "delegate_start_date": today - timedelta(days=1),
                "delegate_end_date": today + timedelta(days=30),
            },
        )
        self.env.flush_all()

    def _field_says(self, user):
        scoped = self.request.with_user(user)
        scoped.invalidate_recordset()
        return scoped.is_pending_my_review

    def _search_says(self, user):
        return self.request in self.env["approval.request"].with_user(user).search(
            [("is_pending_my_review", "=", True)],
        )

    def _can_actually_act(self, user):
        return bool(self.request.with_user(user)._get_current_pending_approver())

    def test_field_search_and_reality_agree_for_the_delegate(self):
        self.assertTrue(self._can_actually_act(self.delegate_user))
        self.assertTrue(self._field_says(self.delegate_user))
        self.assertTrue(self._search_says(self.delegate_user))

    def test_field_search_and_reality_agree_for_the_delegator(self):
        self.assertFalse(self._can_actually_act(self.approver_1))
        self.assertFalse(self._field_says(self.approver_1))
        self.assertFalse(self._search_says(self.approver_1))

    def test_search_negation_is_exact(self):
        not_mine = (
            self.env["approval.request"]
            .with_user(self.delegate_user)
            .search(
                [("is_pending_my_review", "=", False)],
            )
        )
        self.assertNotIn(self.request, not_mine)

    def test_shipped_domains_route_through_the_field(self):
        search_view = self.env.ref("approval.view_approval_search_search")
        self.assertIn("is_pending_my_review", search_view.arch)

        for xmlid in (
            "approval.action_approval_inbox",
            "approval.action_approval_request_to_review",
        ):
            domain = self.env.ref(xmlid).domain
            self.assertIn("is_pending_my_review", domain, xmlid)
            self.assertNotIn("approver_ids", domain, xmlid)

    def test_inbox_action_and_its_default_filter_agree(self):
        action = self.env.ref("approval.action_approval_inbox")
        Request = self.env["approval.request"].with_user(self.delegate_user)
        action_domain = literal_eval(action.domain)
        filter_domain = [("is_pending_my_review", "=", True)]

        self.assertIn(self.request, Request.search(action_domain))
        self.assertIn(self.request, Request.search(action_domain + filter_domain))


@tagged("post_install", "-at_install")
class TestDelegationFrameInternals(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.no_tz_approver = cls.env["res.users"].create(
            {
                "name": "No Timezone",
                "login": "frame_no_tz",
                "email": "frame.notz@test.com",
                "tz": False,
            },
        )
        cls.backup = cls.env["res.users"].create(
            {
                "name": "Frame Backup",
                "login": "frame_backup",
                "email": "frame.backup@test.com",
                "tz": False,
            },
        )
        cls.category = cls._make_category(
            name="Frame Cat",
            approvers=[(cls.no_tz_approver, False, 10)],
        )

    def _delegated_row(self):
        request = self._prepare_request(self.category)
        row = request.approver_ids
        today = row._delegation_today()
        row.sudo().write(
            {
                "delegate_id": self.backup.id,
                "delegate_start_date": today - timedelta(days=1),
                "delegate_end_date": today + timedelta(days=5),
            },
        )
        self.env.flush_all()
        return row

    def test_users_without_a_timezone_are_bucketed(self):
        row = self._delegated_row()
        row.invalidate_recordset(["is_delegated"])

        self.assertTrue(row.is_delegated)
        self.assertIn(
            row,
            self.env["approval.approver"].search(
                [("id", "=", row.id), ("is_delegated", "=", True)],
            ),
            "A NULL timezone must land in a bucket, or the search silently "
            "disagrees with the compute for most of the user base.",
        )
        self.assertNotIn(
            row,
            self.env["approval.approver"].search(
                [("id", "=", row.id), ("is_delegated", "=", False)],
            ),
        )

    def test_timezone_bucket_cache_is_invalidated_on_tz_change(self):
        Approver = self.env["approval.approver"]
        Approver._delegation_date_buckets()
        self.assertIn("approval_delegation_tz_buckets", self.env.cr.cache)

        self.no_tz_approver.write({"tz": "Pacific/Kiritimati"})

        self.assertNotIn(
            "approval_delegation_tz_buckets",
            self.env.cr.cache,
            "A timezone change must drop the memoised bucket map, or the "
            "delegation window is resolved against a stale frame for the "
            "rest of the transaction.",
        )
        self.assertIn(
            "Pacific/Kiritimati",
            [tz for tzs in Approver._delegation_date_buckets().values() for tz in tzs],
        )

    def test_bucket_map_covers_every_timezone_in_use(self):
        buckets = self.env["approval.approver"]._delegation_date_buckets()
        bucketed = {tz for tzs in buckets.values() for tz in tzs}
        in_use = {
            tz
            for (tz,) in self.env["res.users"]
            .sudo()
            .with_context(active_test=False)
            ._read_group([], ["tz"])
        }

        self.assertEqual(
            bucketed,
            in_use,
            "Every timezone present on res.users must appear in exactly one "
            "bucket; a missing one makes its users invisible to the search.",
        )
        self.assertLessEqual(
            len(buckets),
            3,
            "Timezones span [-12, +14], so 'today' can only take three values.",
        )


@tagged("post_install", "-at_install")
class TestDelegationInvalidatesDerivedFlags(ApprovalCommon):
    def test_can_withdraw_clears_when_the_row_is_delegated_away(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category)
        approver = request.approver_ids
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()

        as_original = request.with_user(self.approver_1)
        self.assertTrue(
            as_original.can_withdraw,
            "The approver who approved must be offered the withdraw button.",
        )

        today = fields.Date.context_today(self.env["approval.request"])
        approver.sudo().write(
            {
                "delegate_id": self.approver_2.id,
                "delegate_start_date": today,
                "delegate_end_date": today,
            },
        )

        self.assertFalse(
            as_original.user_approver_state,
            "The original approver is no longer the effective approver.",
        )
        self.assertFalse(
            as_original.can_withdraw,
            "can_withdraw must be invalidated by the delegation write, not "
            "survive on a stale cached value until something else "
            "invalidates the record.",
        )

    def test_delegation_batch_resolves_today_once_per_timezone(self):
        category = self._make_category(
            approvers=[self.approver_1, self.approver_2],
            approval_minimum=2,
        )
        requests = self.env["approval.request"].browse()
        for _ in range(5):
            requests |= self._prepare_request(category, confirm=False)
        approvers = requests.approver_ids
        self.assertGreaterEqual(len(approvers), 10)

        calls = []
        original = type(self.env["approval.approver"])._delegation_today_by_tz

        def counting(self):
            calls.append(len(self))
            return original(self)

        self.patch(
            type(self.env["approval.approver"]),
            "_delegation_today_by_tz",
            counting,
        )
        approvers.invalidate_recordset(["is_delegated"])
        approvers.mapped("is_delegated")

        self.assertLessEqual(
            len(calls),
            1,
            f"Computing is_delegated over {len(approvers)} rows resolved "
            f"'today' {len(calls)} times; it must be resolved once per "
            f"batch (and only for rows that actually carry a window).",
        )


@tagged("post_install", "-at_install")
class TestDelegationScopeIsLiveRequestsOnly(ApprovalCommon):
    def _approved_request_with_a_parked_row(self):
        category = self._make_category(
            name="Parallel Minimum One",
            approvers=[(self.approver_1, False, 10), (self.approver_2, False, 20)],
            approval_minimum=1,
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()
        self.env.flush_all()
        parked = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertEqual(request.state, "approved")
        self.assertEqual(parked.state, "waiting")
        return request, parked

    def _wizard_for(self, user, apply_to="all_future"):
        today = fields.Date.context_today(self.env["approval.request"])
        return (
            self.env["approval.delegate.wizard"]
            .with_user(user)
            .create(
                {
                    "user_id": user.id,
                    "delegate_id": self.manager_user.id,
                    "start_date": today,
                    "end_date": today,
                    "apply_to": apply_to,
                },
            )
        )

    def test_parked_rows_on_an_approved_request_are_not_delegated(self):
        _request, parked = self._approved_request_with_a_parked_row()

        wizard = self._wizard_for(self.approver_2)
        wizard.action_confirm()
        self.env.flush_all()

        self.assertFalse(
            parked.delegate_id,
            "A row parked on an already-approved request must not receive "
            "a delegation.",
        )

    def test_the_preview_does_not_count_them_either(self):
        self._approved_request_with_a_parked_row()

        wizard = self._wizard_for(self.approver_2)

        self.assertEqual(
            wizard.waiting_count,
            0,
            "The preview must count exactly what action_confirm would "
            "delegate; it reads the same domain.",
        )

    def test_waiting_rows_on_a_live_request_are_still_delegated(self):
        category = self._make_category(
            name="Sequential Chain",
            approvers=[(self.approver_1, False, 10), (self.approver_2, False, 20)],
            in_order=True,
            approval_minimum=2,
        )
        request = self._prepare_request(category)
        waiting = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertEqual(request.state, "pending")
        self.assertEqual(waiting.state, "waiting")

        wizard = self._wizard_for(self.approver_2)
        self.assertEqual(wizard.waiting_count, 1)
        wizard.action_confirm()
        self.env.flush_all()

        self.assertEqual(waiting.delegate_id, self.manager_user)


@tagged("post_install", "-at_install")
class TestDelegatedActivityHolder(ApprovalCommon):
    """The approval activity is held by whoever may decide the row that day."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            "Delegated activity", approvers=[(cls.approver_1, True, 10)]
        )
        cls.delegate = cls.approver_2

    def _holders(self, request):
        return request._get_approval_activities().user_id

    def _row(self, request):
        return request.approver_ids.filtered(
            lambda approver: approver.user_id == self.approver_1
        )

    def _delegate(self, request, start, end):
        self._row(request).sudo().write(
            {
                "delegate_id": self.delegate.id,
                "delegate_start_date": start,
                "delegate_end_date": end,
            }
        )

    def test_a_delegation_written_on_the_row_hands_the_activity_over(self):
        request = self._prepare_request(self.category)
        self.assertEqual(self._holders(request), self.approver_1)
        self._delegate_row(self._row(request), self.delegate)
        self.assertEqual(self._holders(request), self.delegate)

    def test_ending_a_delegation_on_the_row_hands_it_back(self):
        request = self._prepare_request(self.category)
        self._delegate_row(self._row(request), self.delegate)
        self._row(request).sudo().write(
            {
                "delegate_id": False,
                "delegate_start_date": False,
                "delegate_end_date": False,
            }
        )
        self.assertEqual(self._holders(request), self.approver_1)

    def test_the_activity_returns_when_the_window_closes(self):
        request = self._prepare_request(self.category)
        today = fields.Date.today()
        self._delegate(request, today, today + timedelta(days=1))
        self.assertEqual(self._holders(request), self.delegate)
        with freeze_time(today + timedelta(days=3)):
            self.env["approval.approver"].invalidate_model(["is_delegated"])
            self.env["approval.approver"].cron_hand_delegated_activities_over()
        self.assertEqual(self._holders(request), self.approver_1)

    def test_the_activity_moves_when_a_scheduled_window_opens(self):
        request = self._prepare_request(self.category)
        today = fields.Date.today()
        self._delegate(request, today + timedelta(days=2), today + timedelta(days=4))
        self.assertEqual(self._holders(request), self.approver_1)
        with freeze_time(today + timedelta(days=3)):
            self.env["approval.approver"].invalidate_model(["is_delegated"])
            self.env["approval.approver"].cron_hand_delegated_activities_over()
        self.assertEqual(self._holders(request), self.delegate)
