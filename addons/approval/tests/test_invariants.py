from datetime import timedelta

from psycopg.errors import IntegrityError

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestOnePersonOneApproval(ApprovalCommon):
    def _delegate(self, row, delegate, days=5):
        today = fields.Date.today()
        row.sudo().write(
            {
                "delegate_id": delegate.id,
                "delegate_start_date": today,
                "delegate_end_date": today + timedelta(days=days),
            },
        )

    def test_delegate_added_to_category_later_does_not_gain_a_second_slot(self):
        category = self._make_category(
            "A4 late co-approver",
            approvers=[(self.approver_1, True, 10)],
            approval_minimum=2,
        )
        request = self._prepare_request(category, confirm=False)
        row_1 = request.approver_ids
        self._delegate(row_1, self.approver_2)

        category._add_approver(self.approver_2, required=True)
        request.write({"amount": 1.0})

        effective = [a._get_effective_approver() for a in request.approver_ids]
        self.assertEqual(
            len(effective),
            len(set(effective)),
            "No user may be the effective approver of two rows on one "
            "request: the delegation constraint said so at delegation time "
            "and the sync must hold the same line when the approver set "
            "grows afterwards.",
        )
        self.assertFalse(
            row_1.delegate_id,
            "the superseded delegation is retired, not silently kept",
        )

    def test_a_single_user_cannot_satisfy_a_two_approver_minimum(self):
        category = self._make_category(
            "A4 two slots",
            approvers=[(self.approver_1, True, 10)],
            approval_minimum=2,
        )
        request = self._prepare_request(category, confirm=False)
        self._delegate(request.approver_ids, self.approver_2)
        category._add_approver(self.approver_2, required=True)
        request.write({"amount": 1.0})
        request.action_confirm()

        own_row = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_2,
        )
        own_row.with_user(self.approver_2).action_approve()

        self.assertEqual(
            request.state,
            "pending",
            "one human clicking Approve once must not satisfy a minimum of 2",
        )

    def test_multi_principal_fan_in_to_a_non_approver_still_works(self):
        third = self.env["res.users"].create(
            {"name": "A4 Third", "login": "a4_third", "email": "a4t@test.com"},
        )
        category = self._make_category(
            "A4 fan-in",
            approvers=[(self.approver_1, False, 10), (self.approver_2, False, 20)],
            approval_minimum=1,
        )
        request = self._prepare_request(category, confirm=False)
        for row in request.approver_ids:
            self._delegate(row, third)
        request.action_confirm()
        self.env.flush_all()

        activities = request.activity_ids.filtered(
            lambda a: (
                a.user_id == third
                and a.activity_type_id
                == self.env.ref("approval.mail_activity_data_approval")
            ),
        )
        self.assertEqual(
            len(activities),
            1,
            "delegation fan-in to somebody holding no approval of their own "
            "is a deliberate feature and must survive the one-person-one-"
            "approval fix",
        )

    def test_delegating_to_an_existing_co_approver_is_still_refused(self):
        category = self._make_category(
            "A4 reverse",
            approvers=[(self.approver_1, False, 10), (self.approver_2, False, 20)],
            approval_minimum=1,
        )
        request = self._prepare_request(category, confirm=False)
        row_1 = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        with self.assertRaises(ValidationError):
            self._delegate(row_1, self.approver_2)

    def test_archive_handover_never_targets_another_rows_delegate(self):
        departing = self.env["res.users"].create(
            {"name": "A4 Leaver", "login": "a4_leaver", "email": "a4l@test.com"},
        )
        category = self._make_category(
            "A4 handover",
            approvers=[(departing, True, 10), (self.approver_1, True, 20)],
            approval_minimum=2,
            escalate_overdue=True,
            escalation_user_id=self.approver_2.id,
        )
        request = self._prepare_request(category, confirm=False)
        row_other = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        self._delegate(row_other, self.approver_2)
        request.action_confirm()

        departing.write({"active": False})

        effective = [a._get_effective_approver() for a in request.approver_ids]
        self.assertEqual(
            len(effective),
            len(set(effective)),
            "the escalation successor must not be somebody already covering "
            "another row on the same request as a delegate",
        )


@tagged("post_install", "-at_install")
class TestApproverUniquenessIsEnforcedInTheDatabase(ApprovalCommon):
    def test_duplicate_approver_rows_are_rejected_on_direct_create(self):
        category = self._make_category(
            "A4 dup row", approvers=[(self.approver_1, True, 10)]
        )
        request = self._prepare_request(category, confirm=False)

        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            self.env["approval.approver"].sudo().with_context(
                approver_ids_computation=True,
            ).create({"request_id": request.id, "user_id": self.approver_1.id})
            self.env.flush_all()


@tagged("post_install", "-at_install")
class TestTerminalDateStamps(ApprovalCommon):
    def test_grant_date_is_restamped_after_withdraw_and_re_approve(self):
        category = self._make_category(
            "A4 stamps", approvers=[(self.approver_1, True, 10)]
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()
        first_grant = request.date_approval_granted
        self.assertTrue(first_grant)

        request.with_user(self.approver_1).action_withdraw()
        self.assertEqual(request.state, "pending")
        self.assertFalse(
            request.date_approval_granted,
            "a withdrawn approval leaves no grant date behind: the metrics "
            "and SLA views key on this column and would otherwise measure a "
            "decision that was revoked",
        )

        later = fields.Datetime.now() + timedelta(seconds=5)
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()
        self.assertTrue(request.date_approval_granted)
        self.assertGreaterEqual(request.date_approval_granted, first_grant)
        self.assertLess(request.date_approval_granted, later)

    def test_only_the_current_states_stamp_is_set(self):
        category = self._make_category(
            "A4 one stamp", approvers=[(self.approver_1, True, 10)]
        )
        request = self._prepare_request(category)
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_approve()
        self.assertTrue(request.date_approval_granted)

        request.with_user(self.manager_user).action_reset_to_draft()
        request.action_confirm()
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_refuse()

        self.assertEqual(request.state, "refused")
        self.assertTrue(request.date_refused)
        self.assertFalse(
            request.date_approval_granted,
            "the stamps are no longer append-only — a refused request must "
            "not still carry the grant date of an earlier approval cycle",
        )


@tagged("post_install", "-at_install")
class TestPendingReviewPredicateHasOneMeaning(ApprovalCommon):
    def _request_with_delegation(self, label, start_offset, end_offset):
        category = self._make_category(label, approvers=[(self.approver_1, True, 10)])
        request = self._prepare_request(category, confirm=False)
        if start_offset is not None:
            today = fields.Date.today()
            request.approver_ids.sudo().write(
                {
                    "delegate_id": self.approver_2.id,
                    "delegate_start_date": today + timedelta(days=start_offset),
                    "delegate_end_date": today + timedelta(days=end_offset),
                },
            )
        request.action_confirm()
        return request

    def test_sql_domain_and_python_resolution_agree_in_every_window(self):
        cases = {
            "no delegation": self._request_with_delegation("D4 none", None, None),
            "active": self._request_with_delegation("D4 active", -1, 1),
            "expired": self._request_with_delegation("D4 expired", -10, -5),
            "future": self._request_with_delegation("D4 future", 5, 10),
        }
        model = self.env["approval.request"]

        for user in (self.approver_1, self.approver_2):
            by_domain = set(
                model.search(model._get_domain_pending_review(user)).ids,
            ) & {request.id for request in cases.values()}
            by_python = {
                request.id
                for request in cases.values()
                if request._get_current_pending_approver(user)
            }
            self.assertEqual(
                by_domain,
                by_python,
                f"the SQL leaves in _get_domain_pending_review and the Python "
                f"resolution in _get_current_pending_approver are two "
                f"spellings of one predicate and must agree for "
                f"{user.login}; they drifted once already and inverted "
                f"delegation, emptying the delegate's inbox while the "
                f"delegator still saw the request",
            )


@tagged("post_install", "-at_install")
class TestPredictionIsCurrencyAware(ApprovalCommon):
    def test_amounts_in_another_currency_are_converted_before_matching(self):
        usd = self.env.ref("base.USD")
        eur = self.env.ref("base.EUR")
        self.env["res.currency.rate"].search([]).unlink()
        self.env["res.currency.rate"].create(
            {
                "name": fields.Date.today(),
                "currency_id": eur.id,
                "rate": 4.0,
                "company_id": self.env.company.id,
            },
        )
        category = self._make_category(
            "A4 currency",
            approvers=[(self.approver_1, True, 10)],
        )
        for _index in range(4):
            historic = self._prepare_request(
                category, amount=1000.0, currency_id=usd.id
            )
            historic.with_user(self.approver_1).with_context(
                skip_wizard=True,
            ).action_approve()

        probe = self._prepare_request(
            category, confirm=False, amount=1000.0, currency_id=eur.id
        )
        self.assertEqual(
            probe._predict_outcome()[0],
            "uncertain",
            "EUR 1000 is USD 250 at this rate and must not match a history "
            "of USD 1000 approvals: every other amount comparison in the "
            "module converts through currency_id first",
        )
