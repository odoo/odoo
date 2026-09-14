from datetime import timedelta

from odoo import fields
from odoo.tests import common, tagged

from .common import (
    ApprovalCommon,
    add_category_approver,
    new_trip_category,
    record_approval,
)


@tagged("post_install", "-at_install")
class TestSLATracking(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "SLA Approver",
                "login": "sla_approver",
                "email": "sla_approver@test.com",
            }
        )
        cls.owner = cls.env.ref("base.user_admin")
        cls.category = new_trip_category(cls.env)
        cls.category.write(
            {
                "sla_target_hours": 24,
                "sla_warning_pct": 80,
            }
        )
        add_category_approver(
            cls.category, cls.approver_user, required=True, sequence=10
        )

    def _create_request(self, **kwargs):
        vals = {
            "name": "SLA Test",
            "category_id": self.category.id,
            "request_owner_id": self.owner.id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
        }
        vals.update(kwargs)
        return self.env["approval.request"].create(vals)

    def _create_and_confirm(self, **kwargs):
        request = self._create_request(**kwargs)
        request.action_confirm()
        return request

    def test_sla_no_sla_when_not_configured(self):
        self.category.sla_target_hours = 0
        request = self._create_and_confirm()
        self.assertEqual(request.sla_status, "no_sla")

    def test_sla_no_sla_before_confirmation(self):
        request = self._create_request()
        self.assertEqual(request.sla_status, "no_sla")

    def test_sla_on_track(self):
        request = self._create_and_confirm()
        self.assertEqual(request.sla_status, "on_track")

    def test_sla_at_risk(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=20)
        request.invalidate_recordset(["sla_status"])
        self.assertEqual(request.sla_status, "at_risk")

    def test_sla_breached(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=30)
        request.invalidate_recordset(["sla_status"])
        self.assertEqual(request.sla_status, "breached")

    def test_sla_met_when_approved_in_time(self):
        request = self._create_and_confirm()
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        record_approval(approver)
        request.invalidate_recordset(["sla_status", "state"])
        self.assertEqual(request.sla_status, "met")

    def test_sla_breached_when_approved_late(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=48)
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        record_approval(approver)
        request.invalidate_recordset(["sla_status", "state"])
        self.assertEqual(request.sla_status, "breached")

    def test_sla_elapsed_hours(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=10)
        request.invalidate_recordset(["sla_elapsed_hours"])
        self.assertAlmostEqual(request.sla_elapsed_hours, 10.0, delta=0.1)

    def test_sla_remaining_hours(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=10)
        request.invalidate_recordset(["sla_remaining_hours"])
        self.assertAlmostEqual(request.sla_remaining_hours, 14.0, delta=0.1)

    def test_sla_remaining_negative_when_breached(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=30)
        request.invalidate_recordset(["sla_remaining_hours"])
        self.assertLess(request.sla_remaining_hours, 0)

    def test_sla_custom_warning_percentage(self):
        self.category.sla_warning_pct = 50
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=13)
        request.invalidate_recordset(["sla_status"])
        self.assertEqual(request.sla_status, "at_risk")

        request.date_confirmed = fields.Datetime.now() - timedelta(hours=11)
        request.invalidate_recordset(["sla_status"])
        self.assertEqual(request.sla_status, "on_track")


@tagged("post_install", "-at_install")
class TestSLAStatusSingleSource(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            name="SLA Agreement",
            approvers=[(cls.approver_1, False, 10)],
            sla_target_hours=10,
            sla_warning_pct=80,
        )
        cls.category_default_pct = cls._make_category(
            name="SLA Agreement Default Pct",
            approvers=[(cls.approver_1, False, 10)],
            sla_target_hours=10,
            sla_warning_pct=0,
        )
        cls.category_no_sla = cls._make_category(
            name="SLA Agreement None",
            approvers=[(cls.approver_1, False, 10)],
            sla_target_hours=0,
        )

    def _aged(self, category, hours, outcome=None):
        request = self._prepare_request(category)
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
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE approval_request SET date_confirmed = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(hours=hours), request.id),
        )
        request.invalidate_recordset()
        return request

    def _matrix(self):
        return (
            self._aged(self.category, 1)
            | self._aged(self.category, 8.5)
            | self._aged(self.category, 11)
            | self._aged(self.category_default_pct, 8.5)
            | self._aged(self.category_default_pct, 2)
            | self._aged(self.category_no_sla, 50)
            | self._aged(self.category, 2, outcome="approved")
            | self._aged(self.category, 40, outcome="approved")
            | self._aged(self.category, 40, outcome="refused")
            | self._aged(self.category, 40, outcome="cancelled")
        )

    def test_search_agrees_with_compute_for_every_status(self):
        requests = self._matrix()
        self.env.flush_all()

        expected = {}
        for request in requests:
            request.invalidate_recordset(["sla_status"])
            expected.setdefault(request.sla_status, self.env["approval.request"])
            expected[request.sla_status] |= request

        self.assertGreaterEqual(
            len(expected),
            4,
            "The fixture must span most statuses or this proves little.",
        )

        for status, wanted in expected.items():
            searched = self.env["approval.request"].search(
                [("id", "in", requests.ids), ("sla_status", "=", status)],
            )
            self.assertEqual(
                searched,
                wanted,
                f"search and compute disagree on {status!r}: the SQL CASE "
                f"in _search_sla_status has drifted from _sla_status_for.",
            )

    def test_search_negation_agrees_too(self):
        requests = self._matrix()
        self.env.flush_all()
        breached = requests.filtered(lambda r: r.sla_status == "breached")

        self.assertEqual(
            self.env["approval.request"].search(
                [("id", "in", requests.ids), ("sla_status", "!=", "breached")],
            ),
            requests - breached,
        )

    def test_default_warning_pct_is_shared_by_both_copies(self):
        request = self._aged(self.category_default_pct, 8.5)
        self.env.flush_all()
        request.invalidate_recordset(["sla_status"])

        self.assertEqual(request.sla_status, "at_risk")
        self.assertIn(
            request,
            self.env["approval.request"].search([("sla_status", "=", "at_risk")]),
        )

    def test_classification_helper_is_the_only_live_rule(self):
        Request = self.env["approval.request"]
        default_pct = Request._SLA_DEFAULT_WARNING_PCT

        self.assertEqual(Request._sla_status_for(1, 10, 80), "on_track")
        self.assertEqual(Request._sla_status_for(8.5, 10, 80), "at_risk")
        self.assertEqual(Request._sla_status_for(11, 10, 80), "breached")
        self.assertEqual(Request._sla_status_for(8, 10, 80), "on_track")
        self.assertEqual(Request._sla_status_for(10, 10, 80), "at_risk")
        self.assertEqual(
            Request._sla_status_for(default_pct / 100 * 10 + 0.1, 10, 0),
            "at_risk",
        )


@tagged("post_install", "-at_install")
class TestSlaPythonAndSqlAgree(ApprovalCommon):
    def _spread(self):
        categories = [
            self._make_category(
                f"SLA {label}",
                approvers=[self.approver_1],
                **vals,
            )
            for label, vals in (
                ("none", {"sla_target_hours": 0}),
                ("p0", {"sla_target_hours": 10, "sla_warning_pct": 0}),
                ("p50", {"sla_target_hours": 10, "sla_warning_pct": 50}),
                ("p80", {"sla_target_hours": 10, "sla_warning_pct": 80}),
            )
        ]
        made = self.env["approval.request"]
        ages = []
        for category in categories:
            for hours in (0, 3, 6, 9, 11, 40):
                for outcome in (None, "approve", "refuse", "cancel"):
                    request = self._prepare_request(category)
                    if outcome == "approve":
                        request.with_user(self.approver_1).action_approve()
                    elif outcome == "refuse":
                        request.with_user(self.approver_1).with_context(
                            skip_wizard=True,
                        ).action_refuse()
                    elif outcome == "cancel":
                        request.action_cancel()
                    made |= request
                    ages.append(hours)
        self.env.flush_all()
        for request, hours in zip(made, ages, strict=True):
            if hours:
                self.env.cr.execute(
                    "UPDATE approval_request SET date_confirmed = "
                    "(NOW() AT TIME ZONE 'UTC') - (%s * INTERVAL '1 hour') "
                    "WHERE id = %s",
                    (hours, request.id),
                )
        self.env.invalidate_all()
        return made

    def test_every_branch_is_reachable_and_both_implementations_agree(self):
        made = self._spread()
        statuses = {request.sla_status for request in made}
        self.assertEqual(
            statuses,
            {"no_sla", "on_track", "at_risk", "breached", "met"},
            "the fixture no longer spans every branch, so agreement below "
            "would be vacuous: %s" % sorted(statuses),
        )
        for status in sorted(statuses):
            by_compute = made.filtered(lambda r, s=status: r.sla_status == s)
            by_search = self.env["approval.request"].search(
                [("id", "in", made.ids), ("sla_status", "=", status)],
            )
            self.assertEqual(
                set(by_compute.ids),
                set(by_search.ids),
                "_compute_sla_status and _search_sla_status disagree on %r" % status,
            )


class TestSlaPolicyIsSnapshotted(ApprovalCommon):
    def test_changing_the_category_sla_does_not_rewrite_a_confirmed_request(self):
        category = self._make_category(
            name="Snapshot SLA", approvers=[self.approver_1], sla_target_hours=10
        )
        request = self._prepare_request(category)
        self.assertEqual(request.sla_status, "on_track")
        self.assertAlmostEqual(request.sla_remaining_hours, 10, delta=0.1)

        category.sla_target_hours = 0
        request.invalidate_recordset()
        self.assertEqual(request.sla_status, "on_track")
        self.assertAlmostEqual(request.sla_remaining_hours, 10, delta=0.1)
        self.assertIn(
            request,
            self.env["approval.request"].search([("sla_status", "=", "on_track")]),
        )

        later = self._prepare_request(category)
        self.assertEqual(later.sla_status, "no_sla")
        self.assertIn(
            later,
            self.env["approval.request"].search([("sla_status", "=", "no_sla")]),
        )
