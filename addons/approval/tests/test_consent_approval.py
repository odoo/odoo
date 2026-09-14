from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from .common import ApprovalCommon, add_category_approver, new_trip_category, pool_step


@tagged("post_install", "-at_install")
class TestConsentApproval(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Consent Approver",
                "login": "consent_approver",
                "email": "consent@test.com",
            }
        )
        cls.owner = cls.env.ref("base.user_admin")
        cls.category = new_trip_category(cls.env)
        cls.category.write(
            {
                "consent_approval_hours": 24,
            }
        )
        add_category_approver(
            cls.category, cls.approver_user, required=True, sequence=10
        )

    def _create_and_confirm(self, **kwargs):
        vals = {
            "name": "Consent Test",
            "category_id": self.category.id,
            "request_owner_id": self.owner.id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
        }
        vals.update(kwargs)
        request = self.env["approval.request"].create(vals)
        request.action_confirm()
        return request

    def test_consent_approves_after_window(self):
        request = self._create_and_confirm()
        self.assertEqual(request.state, "pending")

        request.date_confirmed = fields.Datetime.now() - timedelta(hours=30)
        self.env["approval.request"].cron_consent_approval()
        self.assertEqual(request.state, "approved")

    def test_consent_does_not_approve_within_window(self):
        request = self._create_and_confirm()
        self.assertEqual(request.state, "pending")

        self.env["approval.request"].cron_consent_approval()
        self.assertEqual(request.state, "pending")

    def test_consent_skips_refused_requests(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=30)

        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_user
        )
        approver.sudo()._record_decision("refused")

        self.env["approval.request"].cron_consent_approval()
        self.assertEqual(request.state, "refused")

    def test_consent_disabled_when_zero(self):
        self.category.consent_approval_hours = 0
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=100)

        self.env["approval.request"].cron_consent_approval()
        self.assertEqual(request.state, "pending")

    def test_consent_ignores_non_pending_requests(self):
        request = self._create_and_confirm()
        request.date_confirmed = fields.Datetime.now() - timedelta(hours=30)

        request._refuse_cascade()
        self.assertEqual(request.state, "refused")

        self.env["approval.request"].cron_consent_approval()
        self.assertEqual(request.state, "refused")

    def test_c3_consent_sequential_blocked_by_constraint(self):
        with self.assertRaises(ValidationError):
            self.env["approval.category"].create(
                {
                    "sequence_code": "SC0026",
                    "name": "C3 Category",
                    "approval_minimum": 2,
                    "step_ids": pool_step([], minimum=2, in_order=True),
                    "consent_approval_hours": 1,
                }
            )


@tagged("post_install", "-at_install")
class TestConsentApprovalAuditRegressions(ApprovalCommon):
    def test_consent_cron_locks_before_writing_approver_state(self):
        category = self._make_category(
            approvers=[self.approver_1],
            consent_approval_hours=1,
        )
        with freeze_time("2026-01-01 00:00:00"):
            request = self._prepare_request(category)

        with freeze_time("2026-01-01 05:00:00"):
            with patch.object(
                type(request),
                "_lock_for_approval_action",
                autospec=True,
            ) as mock_lock:
                self.env["approval.request"].cron_consent_approval()

        self.assertTrue(
            mock_lock.called,
            "cron_consent_approval must call _lock_for_approval_action() "
            "before writing approver state.",
        )
        self.assertEqual(request.approver_ids.state, "approved")
