from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from .common import (
    ApprovalCommon,
    add_category_approver,
    add_rule_step,
    new_trip_category,
)


@tagged("post_install", "-at_install")
class TestConditionalRules(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Rule Approver",
                "login": "rule_approver",
                "email": "rule_approver@test.com",
            }
        )
        cls.extra_approver = cls.env["res.users"].create(
            {
                "name": "Extra Approver",
                "login": "extra_approver",
                "email": "extra_approver@test.com",
            }
        )
        cls.category = new_trip_category(cls.env)
        add_category_approver(
            cls.category, cls.approver_user, required=True, sequence=10
        )

    def _rule(self, users, name, field, operator, threshold, active=True):
        return add_rule_step(
            self.category,
            users,
            name=name,
            condition_field=field,
            operator=operator,
            threshold=threshold,
            active=active,
        )

    def _create_request(self, **kwargs):
        vals = {
            "name": "Test Request",
            "category_id": self.category.id,
            "request_owner_id": self.env.ref("base.user_admin").id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
        }
        vals.update(kwargs)
        return self.env["approval.request"].create(vals)

    def test_rule_amount_greater_than(self):
        self._rule(self.extra_approver, "High-Value Purchase", "amount", "gt", 10000)

        request_low = self._create_request(amount=5000)
        approver_users = request_low.approver_ids.mapped("user_id")
        self.assertIn(self.approver_user, approver_users)
        self.assertNotIn(self.extra_approver, approver_users)
        self.assertFalse(request_low.applied_rule_ids)

        request_high = self._create_request(amount=15000)
        approver_users = request_high.approver_ids.mapped("user_id")
        self.assertIn(self.extra_approver, approver_users)
        self.assertEqual(len(request_high.applied_rule_ids), 1)
        self.assertEqual(request_high.applied_rule_ids.name, "High-Value Purchase")

    def test_rule_quantity_less_than(self):
        self._rule(self.extra_approver, "Small Quantity Review", "quantity", "lt", 5)

        self.assertIn(
            self.extra_approver,
            self._create_request(quantity=3).approver_ids.user_id,
        )
        self.assertNotIn(
            self.extra_approver,
            self._create_request(quantity=10).approver_ids.user_id,
        )

    def test_rule_priority_equal(self):
        self._rule(self.extra_approver, "Urgent Review", "priority", "eq", 3)

        self.assertNotIn(
            self.extra_approver,
            self._create_request(priority="1").approver_ids.user_id,
        )
        self.assertIn(
            self.extra_approver,
            self._create_request(priority="3").approver_ids.user_id,
        )

    def test_a_step_never_applies_by_an_archived_rule(self):
        rule = self.env["approval.rule"].create(
            {
                "name": "Archived Rule",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 100,
                "action_type": "condition",
                "active": False,
            }
        )

        request = self._create_request(amount=5000)
        self.assertNotIn(rule, request.applied_rule_ids)
        self.assertNotIn(self.extra_approver, request.approver_ids.user_id)

    def test_rule_multiple_approvers(self):
        third_approver = self.env["res.users"].create(
            {
                "name": "Third Approver",
                "login": "third_approver",
                "email": "third@test.com",
            }
        )
        self._rule(
            self.extra_approver | third_approver,
            "Multi Approver Rule",
            "amount",
            "gte",
            1000,
        )

        approver_users = self._create_request(amount=1000).approver_ids.user_id
        self.assertIn(self.extra_approver, approver_users)
        self.assertIn(third_approver, approver_users)

    def test_rule_priority_threshold_validation(self):
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "name": "Bad Priority",
                    "category_id": self.category.id,
                    "condition_field": "priority",
                    "operator": "eq",
                    "threshold": 5,
                }
            )

    def test_rule_date_range_days(self):
        self._rule(self.extra_approver, "Extended Leave", "date_range_days", "gt", 10)

        now = fields.Datetime.now()
        request_short = self._create_request(
            date_start=now,
            date_end=now + timedelta(days=5),
        )
        self.assertNotIn(self.extra_approver, request_short.approver_ids.user_id)

        request_long = self._create_request(
            date_start=now,
            date_end=now + timedelta(days=15),
        )
        self.assertIn(self.extra_approver, request_long.approver_ids.user_id)

    def test_multiple_rules_same_category(self):
        self._rule(self.extra_approver, "Amount Rule", "amount", "gt", 1000)
        third_approver = self.env["res.users"].create(
            {
                "name": "Priority Approver",
                "login": "priority_approver",
                "email": "priority@test.com",
            }
        )
        self._rule(third_approver, "Priority Rule", "priority", "gte", 2)

        request = self._create_request(amount=5000, priority="3")
        approver_users = request.approver_ids.mapped("user_id")
        self.assertIn(self.extra_approver, approver_users)
        self.assertIn(third_approver, approver_users)
        self.assertEqual(len(request.applied_rule_ids), 2)


@tagged("post_install", "-at_install")
class TestLiveRerouting(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.late_approver = cls.env["res.users"].create(
            {
                "name": "Late Approver",
                "login": "live_late_approver",
                "email": "late@live.test",
            },
        )

    def _urgent_rule(self, category, required=True, sequence=5):
        return add_rule_step(
            category,
            self.late_approver,
            required=required,
            sequence=sequence,
            name="Urgent needs the late approver",
            condition_field="priority",
            operator="gte",
            threshold=3,
        )

    def test_raising_priority_after_submit_adds_the_rule_approver(self):
        category = self._make_category("Live Prio", approvers=[self.approver_1])
        self._urgent_rule(category)
        request = self._prepare_request(category, priority="1")
        self.assertNotIn(self.late_approver, request.approver_ids.user_id)

        request.with_user(self.owner_user).write({"priority": "3"})

        self.assertIn(self.late_approver, request.approver_ids.user_id)

    def test_live_reroute_leaves_the_request_pending(self):
        category = self._make_category("Live State", approvers=[self.approver_1])
        self._urgent_rule(category)
        request = self._prepare_request(category, priority="1")
        confirmed_at = request.date_confirmed

        request.with_user(self.owner_user).write({"priority": "3"})

        self.assertEqual(request.state, "pending")
        self.assertEqual(request.date_confirmed, confirmed_at)
        added = request.approver_ids.filtered(
            lambda a: a.user_id == self.late_approver,
        )
        self.assertEqual(added.state, "pending")
        self.assertFalse(request.approver_ids.filtered(lambda a: a.state == "new"))

    def test_live_reroute_preserves_decisions_already_recorded(self):
        category = self._make_category(
            "Live Keep",
            approvers=[self.approver_1, self.approver_2],
        )
        self._urgent_rule(category, required=False)
        request = self._prepare_request(category, priority="1")
        request.with_user(self.approver_1).action_approve()
        decided = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        decision_date = decided.decision_date

        request.with_user(self.owner_user).write({"priority": "3"})

        self.assertEqual(decided.state, "approved")
        self.assertEqual(decided.decision_date, decision_date)
        self.assertIn(self.late_approver, request.approver_ids.user_id)

    def test_live_reroute_never_touches_a_terminal_request(self):
        category = self._make_category("Live Terminal", approvers=[self.approver_1])
        self._urgent_rule(category)
        request = self._prepare_request(category, priority="1")
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")

        request.with_user(self.manager_user).write({"priority": "3"})

        self.assertEqual(request.state, "approved")
        self.assertNotIn(self.late_approver, request.approver_ids.user_id)

    def test_live_reroute_keeps_an_approver_whose_source_stopped_matching(self):
        category = self._make_category("Live Orphan", approvers=[self.approver_1])
        self._urgent_rule(category, required=False)
        request = self._prepare_request(category, priority="3")
        self.assertIn(self.late_approver, request.approver_ids.user_id)

        request.with_user(self.owner_user).write({"priority": "1"})

        self.assertIn(self.late_approver, request.approver_ids.user_id)

    def test_live_reroute_asks_an_arriving_step_beside_an_ordered_one(self):
        category = self._make_category(
            "Live Sequential",
            approvers=[(self.approver_1, True, 10), (self.approver_2, True, 20)],
            in_order=True,
        )
        self._urgent_rule(category, required=True, sequence=5)
        request = self._prepare_request(category, priority="1")
        request.with_user(self.approver_1).action_approve()

        request.with_user(self.owner_user).write({"priority": "3"})

        added = request.approver_ids.filtered(
            lambda a: a.user_id == self.late_approver,
        )
        second = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_2,
        )
        self.assertEqual(added.state, "pending")
        self.assertEqual(second.state, "pending")

        request.with_user(self.late_approver).action_approve()
        self.assertEqual(request.state, "pending")

        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")

    def test_live_reroute_ignores_configuration_added_after_submission(self):
        category = self._make_category("Live Config", approvers=[self.approver_1])
        self._urgent_rule(category, required=False)
        request = self._prepare_request(category, priority="1")
        category._add_approver(self.approver_2, sequence=20)

        request.with_user(self.owner_user).write({"priority": "3"})

        self.assertIn(self.late_approver, request.approver_ids.user_id)
        self.assertNotIn(self.approver_2, request.approver_ids.user_id)
        self.assertEqual(request.approval_minimum, 2)


@tagged("post_install", "-at_install")
class TestRoutingFieldLifecycle(ApprovalCommon):
    def _sets(self):
        request = self.env["approval.request"]
        return (
            request._get_routing_fields_frozen(),
            request._get_routing_fields_live(),
            request._get_fields_approver_sync_trigger(),
        )

    def test_the_split_is_exhaustive_and_disjoint(self):
        frozen, live, triggers = self._sets()
        self.assertEqual(frozen | live, triggers)
        self.assertFalse(frozen & live)

    def test_every_rule_and_tier_condition_is_classified(self):
        _frozen, _live, triggers = self._sets()
        declared = (
            self.env["approval.rule"]._get_fields_request_trigger()
            | self.env["approval.rule"]._get_fields_request_trigger()
        )
        self.assertFalse(
            declared - triggers,
            "these rule/tier condition inputs reach no lifecycle bucket: %s"
            % sorted(declared - triggers),
        )

    def test_frozen_routing_inputs_really_cannot_move_after_submission(self):
        frozen, _live, _triggers = self._sets()
        request = self.env["approval.request"]
        locked = request._LOCKED_FIELDS | request._SYSTEM_LOCKED_FIELDS
        unprotected = frozen - locked - {"category_id"}
        self.assertFalse(
            unprotected,
            "these routing inputs are treated as frozen but nothing stops a "
            "submitted request from changing them, so the approver set they "
            "feed would go stale silently: %s" % sorted(unprotected),
        )

    def test_live_routing_inputs_are_actually_reachable_after_submission(self):
        _frozen, live, _triggers = self._sets()
        request = self.env["approval.request"]
        locked = request._LOCKED_FIELDS | request._SYSTEM_LOCKED_FIELDS
        reopened = frozenset().union(*request._PENDING_CHANGE_EDITABLE.values())
        unreachable = {f for f in live if f in locked and f not in reopened}
        self.assertFalse(
            unreachable,
            "these are classified live but can never move after submission, "
            "so the live path carries them for nothing: %s" % sorted(unreachable),
        )


class TestRuleScopeFollowsCategory(ApprovalCommon):
    def test_rule_company_defaults_to_its_category(self):
        other = self.env["res.company"].create({"name": "Rule Scope Co"})
        (self.owner_user | self.approver_1 | self.approver_2).write(
            {"company_ids": [(4, other.id)]}
        )
        category = self._make_category(
            name="Scoped", approvers=[self.approver_1], company_id=other.id
        )
        rule = self.env["approval.rule"].create(
            {
                "name": "scoped rule",
                "category_id": category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 1,
                "action_type": "condition",
            }
        )
        self.assertEqual(rule.company_id, other)
        self.assertEqual(rule.currency_id, other.currency_id)

    def test_rule_company_cannot_contradict_its_category(self):
        other = self.env["res.company"].create({"name": "Rule Scope Co 2"})
        category = self._make_category(name="Scoped 2", approvers=[self.approver_1])
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "name": "wrong company",
                    "category_id": category.id,
                    "company_id": other.id,
                    "condition_field": "amount",
                    "operator": "gt",
                    "threshold": 1,
                    "action_type": "condition",
                }
            )

    def test_rule_on_a_global_category_is_global(self):
        category = self._make_category(
            name="Global", approvers=[self.approver_1], company_id=False
        )
        rule = self.env["approval.rule"].create(
            {
                "name": "global rule",
                "category_id": category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 1,
                "action_type": "condition",
            }
        )
        self.assertFalse(rule.company_id)
        self.assertEqual(rule.currency_id, self.env.company.currency_id)


class TestRulesAreEvaluatedOnce(ApprovalCommon):
    def test_one_evaluation_per_step_rule_per_sync(self):
        category = self._make_category(name="Once", approvers=[self.approver_1])
        add_rule_step(
            category,
            self.approver_2,
            name="adds two",
            condition_field="amount",
            operator="gt",
            threshold=1,
        )
        rule_cls = self.env.registry["approval.rule"]
        calls = []
        original = rule_cls._evaluate

        def counting(rule, request):
            calls.append(rule.id)
            return original(rule, request)

        with patch.object(rule_cls, "_evaluate", counting):
            request = self._prepare_request(category, confirm=False, amount=50)
        self.assertEqual(len(calls), 1)
        self.assertIn(self.approver_2, request.approver_ids.user_id)
