from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import ApprovalCommon

DECLINED = (AccessError, UserError, ValidationError)

# Each script is a list of (action, state, who could approve, who holds an
# approval activity), read after the action. The first action is None: the
# request as confirmed.
SCRIPTS = {
    "any_one_of_two": [
        (None, "pending", {"a", "b"}, {"a", "b"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "two_of_two": [
        (None, "pending", {"a", "b"}, {"a", "b"}),
        (("approve", "a"), "pending", {"b"}, {"b"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "required_beside_optional": [
        (None, "pending", {"a", "b"}, {"a", "b"}),
        (("approve", "b"), "pending", {"a"}, {"a"}),
        (("approve", "a"), "approved", set(), set()),
    ],
    "sequential": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "pending", {"b"}, {"b"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "sequential_with_a_rule_approver": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "pending", {"c"}, {"c"}),
        (("approve", "c"), "pending", {"b"}, {"b"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "sequential_withdrawal": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "pending", {"b"}, {"b"}),
        (("withdraw", "a"), "pending", {"a"}, {"a"}),
    ],
    "sequential_quorum_of_one": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "approved", set(), set()),
    ],
    # Separate steps notified in order: a later step's member may decide before the
    # first step is met, which is documented step behaviour, not sequential approval.
    "sequential_as_steps": [
        (None, "pending", {"a", "b"}, {"a"}),
        (("approve", "a"), "pending", {"b"}, {"b"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "one_refusal": [
        (None, "pending", {"a", "b"}, {"a", "b"}),
        (("refuse", "a"), "refused", set(), set()),
    ],
    "withdrawal": [
        (None, "pending", {"a", "b"}, {"a", "b"}),
        (("approve", "a"), "pending", {"b"}, {"b"}),
        (("withdraw", "a"), "pending", {"a", "b"}, {"a", "b"}),
    ],
    "group_queue": [
        (None, "pending", {"c", "d"}, set()),
        (("approve", "d"), "approved", set(), set()),
    ],
    "group_two_members": [
        (None, "pending", {"c", "d"}, set()),
        (("approve", "c"), "pending", {"d"}, set()),
        (("approve", "d"), "approved", set(), set()),
    ],
    "group_asks_its_members": [
        (None, "pending", {"c", "d"}, {"c", "d"}),
        (("approve", "d"), "approved", set(), set()),
    ],
    "group_with_a_rule_approver": [
        (None, "pending", {"b", "c", "d"}, {"b"}),
        (("approve", "c"), "pending", {"b", "d"}, {"b"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "group_with_a_rule_approver_asking_members": [
        (None, "pending", {"b", "c", "d"}, {"b", "c", "d"}),
        (("approve", "c"), "pending", {"b", "d"}, {"b", "d"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "owner_not_asked": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "approved", set(), set()),
    ],
    "rule_adds_a_required_approver": [
        (None, "pending", {"a", "c"}, {"a", "c"}),
        (("approve", "a"), "pending", {"c"}, {"c"}),
        (("approve", "c"), "approved", set(), set()),
    ],
    "rule_adds_an_optional_approver": [
        (None, "pending", {"a", "c"}, {"a", "c"}),
        (("approve", "a"), "approved", set(), set()),
    ],
    "rule_below_its_threshold": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "approved", set(), set()),
    ],
    "tiers_above_both": [
        (None, "pending", {"a", "c", "d"}, {"a", "c", "d"}),
        (("approve", "a"), "pending", {"c", "d"}, {"c", "d"}),
        (("approve", "c"), "pending", {"d"}, {"d"}),
        (("approve", "d"), "approved", set(), set()),
    ],
    "optional_tiers_above_both": [
        (None, "pending", {"a", "c", "d"}, {"a", "c", "d"}),
        (("approve", "a"), "approved", set(), set()),
    ],
    "tiers_between": [
        (None, "pending", {"a", "c"}, {"a", "c"}),
        (("approve", "c"), "approved", set(), set()),
    ],
    "band_replaces_the_approvers": [
        (None, "pending", {"b"}, {"b"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "added_by_hand_counts": [
        (None, "pending", {"a", "d"}, {"a", "d"}),
        (("approve", "a"), "pending", {"d"}, {"d"}),
        (("approve", "d"), "approved", set(), set()),
    ],
    "added_by_hand_joins_the_sequence": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "pending", {"d"}, {"d"}),
        (("approve", "d"), "pending", {"b"}, {"b"}),
        (("approve", "b"), "approved", set(), set()),
    ],
    "only_added_by_hand": [
        (None, "pending", {"c", "d"}, {"c", "d"}),
        (("approve", "c"), "approved", set(), set()),
    ],
    "band_with_a_rule_approver": [
        (None, "pending", {"b", "c"}, {"b", "c"}),
        (("approve", "b"), "pending", {"c"}, {"c"}),
        (("approve", "c"), "approved", set(), set()),
    ],
    "upper_band": [
        (None, "pending", {"c"}, {"c"}),
        (("approve", "c"), "approved", set(), set()),
    ],
    "delegated_approver": [
        (None, "pending", {"b", "d"}, {"b", "d"}),
        (("approve", "d"), "approved", set(), set()),
    ],
    "owner_allowed": [
        (None, "pending", {"owner", "a"}, {"owner", "a"}),
        (("approve", "owner"), "approved", set(), set()),
    ],
}


class _Probe(Exception):
    pass


class RoutingOutcomesCase(ApprovalCommon):
    """What a category's routing does, stated in terms no implementation owns.

    After every decision a script records the request's state, who could approve it
    at that moment (tried inside a savepoint that is rolled back), and who holds an
    approval activity. The flat approver list and the step model are each given the
    same scripts; a merge of the two is held to both classes.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_approver = cls.env.ref("approval.group_approval_approver")
        cls.people = {"owner": cls.owner_user}
        for key in ("a", "b", "c", "d"):
            cls.people[key] = cls.env["res.users"].create(
                {
                    "name": f"Routing {key.upper()}",
                    "login": f"routing_outcome_{key}",
                    "email": f"routing_{key}@test.com",
                    "group_ids": [(4, group_approver.id)],
                }
            )
        cls.pool = cls.env["res.groups"].create(
            {
                "name": "Routing Pool",
                "user_ids": [(6, 0, [cls.people["c"].id, cls.people["d"].id])],
            }
        )

    def _decidable(self, request):
        keys = set()
        for key, user in self.people.items():
            try:
                with self.env.cr.savepoint():
                    request.with_user(user).action_approve()
                    raise _Probe
            except _Probe:
                keys.add(key)
            except DECLINED:
                pass
        return keys

    def _notified(self, request):
        activity_users = request._get_approval_activities().user_id
        return {key for key, user in self.people.items() if user in activity_users}

    def _act(self, request, verb, key):
        actor = request.with_user(self.people[key])
        if verb == "approve":
            actor.action_approve()
        elif verb == "refuse":
            actor.with_context(skip_wizard=True).action_refuse()
        elif verb == "withdraw":
            actor.action_withdraw()
        request.invalidate_recordset()

    def _run(
        self,
        category,
        script_name,
        request_vals=None,
        after_confirm=None,
        added_by_hand=(),
    ):
        request = self._prepare_request(category, confirm=False, **(request_vals or {}))
        for key in added_by_hand:
            self.env["approval.approver"].create(
                {"request_id": request.id, "user_id": self.people[key].id}
            )
        request.action_confirm()
        if after_confirm:
            after_confirm(request)
            request.invalidate_recordset()
        for index, (action, state, decidable, notified) in enumerate(
            SCRIPTS[script_name]
        ):
            if action:
                self._act(request, *action)
            with self.subTest(step=index, action=action):
                self.assertEqual(request.state, state)
                self.assertEqual(self._decidable(request), decidable)
                self.assertEqual(self._notified(request), notified)


@tagged("post_install", "-at_install")
class TestFlatRoutingOutcomes(RoutingOutcomesCase):
    def _flat(self, approvers, **vals):
        category = self._make_category(
            f"Flat routing {self._next_sequence_code()}",
            approvers=[
                (self.people[key], required, sequence)
                for key, required, sequence in approvers
            ],
            **vals,
        )
        if "approval_minimum" in vals:
            category.approval_minimum = vals["approval_minimum"]
        return category

    def test_any_one_of_two(self):
        self._run(
            self._flat([("a", False, 10), ("b", False, 20)], approval_minimum=1),
            "any_one_of_two",
        )

    def test_two_of_two(self):
        self._run(
            self._flat([("a", False, 10), ("b", False, 20)], approval_minimum=2),
            "two_of_two",
        )

    def test_required_beside_optional(self):
        self._run(
            self._flat([("a", True, 10), ("b", False, 20)], approval_minimum=1),
            "required_beside_optional",
        )

    def test_sequential(self):
        self._run(
            self._flat(
                [("a", True, 10), ("b", True, 20)],
                approval_minimum=2,
                approve_sequentially=True,
            ),
            "sequential",
        )

    def test_sequential_withdrawal(self):
        self._run(
            self._flat(
                [("a", True, 10), ("b", True, 20)],
                approval_minimum=2,
                approve_sequentially=True,
            ),
            "sequential_withdrawal",
        )

    def test_sequential_quorum_of_one(self):
        self._run(
            self._flat(
                [("a", False, 10), ("b", False, 20)],
                approval_minimum=1,
                approve_sequentially=True,
            ),
            "sequential_quorum_of_one",
        )

    def test_one_refusal(self):
        self._run(
            self._flat([("a", False, 10), ("b", False, 20)], approval_minimum=1),
            "one_refusal",
        )

    def test_withdrawal(self):
        self._run(
            self._flat([("a", False, 10), ("b", False, 20)], approval_minimum=2),
            "withdrawal",
        )

    def test_group_queue(self):
        self._run(
            self._flat(
                [("a", True, 10)],
                approval_minimum=1,
                group_approval="exclusive",
                approver_group_id=self.pool.id,
            ),
            "group_queue",
        )

    def test_group_two_members(self):
        self._run(
            self._flat(
                [],
                approval_minimum=2,
                group_approval="exclusive",
                approver_group_id=self.pool.id,
            ),
            "group_two_members",
        )

    def test_group_asks_its_members(self):
        self._run(
            self._flat(
                [],
                approval_minimum=1,
                group_approval="exclusive",
                approver_group_id=self.pool.id,
                notify_pool_members=True,
            ),
            "group_asks_its_members",
        )

    def test_a_group_ignores_a_replacement_band(self):
        category = self._flat(
            [],
            approval_minimum=1,
            group_approval="exclusive",
            approver_group_id=self.pool.id,
            has_amount="required",
        )
        self.env["approval.rule"].create(
            {
                "name": "Band over a group",
                "category_id": category.id,
                "condition_type": "threshold",
                "condition_field": "amount",
                "operator": "gte",
                "threshold": 1000,
                "action_type": "set_approvers",
                "approver_ids": [(6, 0, [self.people["b"].id])],
            }
        )
        self._run(category, "group_queue", request_vals={"amount": 5000})

    def _group_rule_category(self, **vals):
        category = self._flat(
            [],
            approval_minimum=1,
            group_approval="exclusive",
            approver_group_id=self.pool.id,
            has_amount="required",
            **vals,
        )
        self.env["approval.rule"].create(
            {
                "name": "Routing rule over a group",
                "category_id": category.id,
                "condition_type": "threshold",
                "condition_field": "amount",
                "operator": "gte",
                "threshold": 1000,
                "action_type": "add_approver",
                "approver_ids": [(6, 0, [self.people["b"].id])],
            }
        )
        return category

    def test_group_with_a_rule_approver(self):
        self._run(
            self._group_rule_category(),
            "group_with_a_rule_approver",
            request_vals={"amount": 5000},
        )

    def test_group_with_a_rule_approver_below_its_threshold(self):
        self._run(
            self._group_rule_category(), "group_queue", request_vals={"amount": 10}
        )

    def test_group_with_a_rule_approver_asking_members(self):
        self._run(
            self._group_rule_category(notify_pool_members=True),
            "group_with_a_rule_approver_asking_members",
            request_vals={"amount": 5000},
        )

    def test_owner_not_asked(self):
        self._run(
            self._flat([("owner", False, 10), ("a", False, 20)], approval_minimum=1),
            "owner_not_asked",
        )

    def test_owner_allowed(self):
        self._run(
            self._flat(
                [("owner", False, 10), ("a", False, 20)],
                approval_minimum=1,
                allow_self_approval=True,
            ),
            "owner_allowed",
        )

    def _amount_category(self, action_type, rule_users, **rule_vals):
        category = self._flat(
            [("a", False, 10)], approval_minimum=1, has_amount="required"
        )
        self.env["approval.rule"].create(
            {
                "name": "Routing rule",
                "category_id": category.id,
                "condition_type": "threshold",
                "condition_field": "amount",
                "action_type": action_type,
                "approver_ids": [(6, 0, [self.people[k].id for k in rule_users])],
                **rule_vals,
            }
        )
        return category

    def test_rule_adds_a_required_approver(self):
        category = self._amount_category(
            "add_approver", ["c"], operator="gte", threshold=1000
        )
        self._run(
            category, "rule_adds_a_required_approver", request_vals={"amount": 5000}
        )

    def test_rule_below_its_threshold(self):
        category = self._amount_category(
            "add_approver", ["c"], operator="gte", threshold=1000
        )
        self._run(category, "rule_below_its_threshold", request_vals={"amount": 10})

    def test_rule_adds_an_optional_approver(self):
        category = self._amount_category(
            "add_approver",
            ["c"],
            operator="gte",
            threshold=1000,
            approver_required=False,
        )
        self._run(
            category, "rule_adds_an_optional_approver", request_vals={"amount": 5000}
        )

    def test_optional_tiers_above_both(self):
        category = self._tiers_category()
        category.rule_ids.approver_required = False
        self._run(category, "optional_tiers_above_both", request_vals={"amount": 9000})

    def test_an_approver_added_by_hand_counts_toward_the_minimum(self):
        self._run(
            self._flat([("a", False, 10)], approval_minimum=2),
            "added_by_hand_counts",
            added_by_hand=["d"],
        )

    def test_a_category_whose_approvers_are_all_added_by_hand(self):
        self._run(
            self._flat([], approval_minimum=1),
            "only_added_by_hand",
            added_by_hand=["c", "d"],
        )

    def test_an_approver_added_by_hand_joins_a_sequence(self):
        self._run(
            self._flat(
                [("a", True, 10), ("b", True, 20)],
                approval_minimum=2,
                approve_sequentially=True,
            ),
            "added_by_hand_joins_the_sequence",
            added_by_hand=["d"],
        )

    def _sequential_rule_category(self):
        category = self._flat(
            [("a", True, 10), ("b", True, 20)],
            approval_minimum=2,
            approve_sequentially=True,
            has_amount="required",
        )
        self.env["approval.rule"].create(
            {
                "name": "Routing rule inside a sequence",
                "category_id": category.id,
                "condition_type": "threshold",
                "condition_field": "amount",
                "operator": "gte",
                "threshold": 1000,
                "action_type": "add_approver",
                "approver_sequence": 15,
                "approver_ids": [(6, 0, [self.people["c"].id])],
            }
        )
        return category

    def test_a_rule_approver_takes_its_place_in_a_sequence(self):
        self._run(
            self._sequential_rule_category(),
            "sequential_with_a_rule_approver",
            request_vals={"amount": 5000},
        )

    def test_a_sequence_below_its_rule_threshold(self):
        self._run(
            self._sequential_rule_category(),
            "sequential",
            request_vals={"amount": 10},
        )

    def _tiers_category(self):
        category = self._amount_category(
            "add_approver", ["c"], operator="gte", threshold=1000
        )
        self.env["approval.rule"].create(
            {
                "name": "Routing rule, upper tier",
                "category_id": category.id,
                "condition_type": "threshold",
                "condition_field": "amount",
                "operator": "gte",
                "threshold": 5000,
                "action_type": "add_approver",
                "approver_ids": [(6, 0, [self.people["d"].id])],
            }
        )
        return category

    def test_tiers_above_both(self):
        self._run(
            self._tiers_category(), "tiers_above_both", request_vals={"amount": 9000}
        )

    def test_tiers_between(self):
        self._run(
            self._tiers_category(), "tiers_between", request_vals={"amount": 2000}
        )

    def test_tiers_below_both(self):
        self._run(
            self._tiers_category(),
            "rule_below_its_threshold",
            request_vals={"amount": 10},
        )

    def _figures_category(self, **vals):
        return self._flat(
            [("a", False, 10)],
            approval_minimum=1,
            has_amount="required",
            has_quantity="required",
            **vals,
        )

    def _rule(self, category, action_type, users, **vals):
        return self.env["approval.rule"].create(
            {
                "name": f"Routing rule {self._next_sequence_code()}",
                "category_id": category.id,
                "condition_type": "threshold",
                "operator": "gte",
                "action_type": action_type,
                "approver_ids": [(6, 0, [self.people[key].id for key in users])],
                **vals,
            }
        )

    def _rules_on_two_figures_category(self):
        category = self._figures_category()
        self._rule(
            category, "add_approver", ["c"], condition_field="amount", threshold=1000
        )
        self._rule(
            category, "add_approver", ["d"], condition_field="quantity", threshold=5
        )
        return category

    def test_rules_on_two_figures_both_match(self):
        self._run(
            self._rules_on_two_figures_category(),
            "tiers_above_both",
            request_vals={"amount": 5000, "quantity": 10},
        )

    def test_rules_on_two_figures_one_matches(self):
        self._run(
            self._rules_on_two_figures_category(),
            "rule_adds_a_required_approver",
            request_vals={"amount": 5000, "quantity": 1},
        )

    def test_rules_on_two_figures_neither_matches(self):
        self._run(
            self._rules_on_two_figures_category(),
            "rule_below_its_threshold",
            request_vals={"amount": 10, "quantity": 1},
        )

    def _band_and_rule_category(self):
        category = self._figures_category()
        self._rule(
            category,
            "set_approvers",
            ["b"],
            condition_field="amount",
            threshold=1000,
            approval_minimum=1,
        )
        self._rule(
            category, "add_approver", ["c"], condition_field="quantity", threshold=5
        )
        return category

    def test_a_band_beside_a_rule_both_match(self):
        self._run(
            self._band_and_rule_category(),
            "band_with_a_rule_approver",
            request_vals={"amount": 5000, "quantity": 10},
        )

    def test_a_band_beside_a_rule_only_the_rule_matches(self):
        self._run(
            self._band_and_rule_category(),
            "rule_adds_a_required_approver",
            request_vals={"amount": 10, "quantity": 10},
        )

    def test_a_band_beside_a_rule_only_the_band_matches(self):
        self._run(
            self._band_and_rule_category(),
            "band_replaces_the_approvers",
            request_vals={"amount": 5000, "quantity": 1},
        )

    def _bands_on_two_figures_category(self):
        category = self._figures_category()
        self._rule(
            category,
            "set_approvers",
            ["b"],
            condition_field="amount",
            threshold=1000,
            approval_minimum=1,
            sequence=10,
        )
        self._rule(
            category,
            "set_approvers",
            ["c"],
            condition_field="quantity",
            threshold=5,
            approval_minimum=1,
            sequence=20,
        )
        return category

    def test_bands_on_two_figures_the_first_wins(self):
        self._run(
            self._bands_on_two_figures_category(),
            "band_replaces_the_approvers",
            request_vals={"amount": 5000, "quantity": 10},
        )

    def test_bands_on_two_figures_the_second_alone(self):
        self._run(
            self._bands_on_two_figures_category(),
            "upper_band",
            request_vals={"amount": 10, "quantity": 10},
        )

    def test_a_rule_on_a_figure_a_request_may_lack(self):
        category = self._flat(
            [("a", False, 10)], approval_minimum=1, has_date_range="optional"
        )
        self._rule(
            category,
            "add_approver",
            ["c"],
            condition_field="date_range_days",
            threshold=2,
        )
        self._run(category, "rule_below_its_threshold")

    def test_a_rule_on_a_figure_a_request_has(self):
        category = self._flat(
            [("a", False, 10)], approval_minimum=1, has_date_range="optional"
        )
        self._rule(
            category,
            "add_approver",
            ["c"],
            condition_field="date_range_days",
            threshold=2,
        )
        self._run(
            category,
            "rule_adds_a_required_approver",
            request_vals={
                "date_start": "2026-01-01 08:00:00",
                "date_end": "2026-01-06 08:00:00",
            },
        )

    def _two_bands_category(self):
        category = self._amount_category(
            "set_approvers",
            ["b"],
            operator="between",
            threshold=1000,
            threshold_max=5000,
            approval_minimum=1,
        )
        self.env["approval.rule"].create(
            {
                "name": "Routing band, upper",
                "category_id": category.id,
                "condition_type": "threshold",
                "condition_field": "amount",
                "operator": "gte",
                "threshold": 5000,
                "action_type": "set_approvers",
                "approval_minimum": 1,
                "approver_ids": [(6, 0, [self.people["c"].id])],
            }
        )
        return category

    def test_two_bands_below_both(self):
        self._run(
            self._two_bands_category(),
            "rule_below_its_threshold",
            request_vals={"amount": 10},
        )

    def test_two_bands_lower(self):
        self._run(
            self._two_bands_category(),
            "band_replaces_the_approvers",
            request_vals={"amount": 2000},
        )

    def test_two_bands_upper(self):
        self._run(
            self._two_bands_category(), "upper_band", request_vals={"amount": 9000}
        )

    def test_a_closed_band_leaves_the_approvers_above_it(self):
        category = self._amount_category(
            "set_approvers",
            ["b"],
            operator="between",
            threshold=1000,
            threshold_max=5000,
            approval_minimum=1,
        )
        self._run(category, "rule_below_its_threshold", request_vals={"amount": 9000})

    def test_band_replaces_the_approvers(self):
        category = self._amount_category(
            "set_approvers",
            ["b"],
            operator="between",
            threshold=1000,
            threshold_max=0,
            approval_minimum=1,
        )
        self._run(
            category, "band_replaces_the_approvers", request_vals={"amount": 5000}
        )

    def test_delegated_approver(self):
        category = self._flat([("a", False, 10), ("b", False, 20)], approval_minimum=1)

        def delegate_a_to_d(request):
            row = request.approver_ids.filtered(
                lambda approver: approver.user_id == self.people["a"]
            )
            self._delegate_row(row, self.people["d"])

        self._run(category, "delegated_approver", after_confirm=delegate_a_to_d)


@tagged("post_install", "-at_install")
class TestStepRoutingOutcomes(RoutingOutcomesCase):
    """The same scripts on categories built from steps, the flat list left empty."""

    def _stepped(self, steps, **vals):
        category = self._make_category(
            f"Step routing {self._next_sequence_code()}", **vals
        )
        for index, (keys, minimum, step_vals) in enumerate(steps):
            self.env["approval.category.step"].create(
                {
                    "category_id": category.id,
                    "name": f"Step {index}",
                    "sequence": step_vals.pop("sequence", 10 * (index + 1)),
                    "minimum": minimum,
                    "member_ids": [
                        Command.create(
                            {"user_id": self.people[key].id, "sequence": 10 * position}
                        )
                        for position, key in enumerate(keys, start=1)
                    ],
                    **step_vals,
                }
            )
        return category

    def test_any_one_of_two(self):
        self._run(self._stepped([(("a", "b"), 1, {})]), "any_one_of_two")

    def test_two_of_two(self):
        self._run(self._stepped([(("a", "b"), 2, {})]), "two_of_two")

    def test_required_beside_optional(self):
        # A required approver is a step of their own, open beside the pool.
        self._run(
            self._stepped(
                [(("a",), 1, {"sequence": 10}), (("a", "b"), 1, {"sequence": 10})]
            ),
            "required_beside_optional",
        )

    def test_sequential(self):
        # Sequential approvers are one step whose members decide in order.
        self._run(self._stepped([(("a", "b"), 2, {"in_order": True})]), "sequential")

    def test_sequential_withdrawal(self):
        self._run(
            self._stepped([(("a", "b"), 2, {"in_order": True})]),
            "sequential_withdrawal",
        )

    def test_sequential_quorum_of_one(self):
        self._run(
            self._stepped([(("a", "b"), 1, {"in_order": True})]),
            "sequential_quorum_of_one",
        )

    def test_separate_steps_order_who_is_asked_not_who_decides(self):
        # Steps of their own, notified in order, are not sequential approval: a
        # later step's member may decide before the first step is met.
        self._run(
            self._stepped([(("a",), 1, {}), (("b",), 1, {})], notify_sequentially=True),
            "sequential_as_steps",
        )

    def test_members_in_order_refuse_consent_approval(self):
        category = self._stepped([(("a", "b"), 1, {"in_order": True})])
        with self.assertRaises(ValidationError):
            category.consent_approval_hours = 24
        consenting = self._stepped([(("a", "b"), 1, {})], consent_approval_hours=24)
        with self.assertRaises(ValidationError):
            consenting.step_ids.in_order = True

    def test_members_in_order_need_listed_members(self):
        with self.assertRaises(ValidationError):
            self._stepped([(("a",), 1, {"in_order": True, "group_id": self.pool.id})])

    def test_one_refusal(self):
        self._run(self._stepped([(("a", "b"), 1, {})]), "one_refusal")

    def test_withdrawal(self):
        self._run(self._stepped([(("a", "b"), 2, {})]), "withdrawal")

    def test_group_queue(self):
        self._run(self._stepped([((), 1, {"group_id": self.pool.id})]), "group_queue")

    def test_group_two_members(self):
        self._run(
            self._stepped([((), 2, {"group_id": self.pool.id})]),
            "group_two_members",
        )

    def test_owner_not_asked(self):
        self._run(self._stepped([(("owner", "a"), 1, {})]), "owner_not_asked")

    def test_owner_allowed(self):
        self._run(
            self._stepped([(("owner", "a"), 1, {})], allow_self_approval=True),
            "owner_allowed",
        )

    def _amount_steps(self, steps):
        return self._stepped(steps, has_amount="required")

    def test_rule_adds_a_required_approver(self):
        # The rule's approver is a step of its own, applicable above the threshold.
        category = self._amount_steps(
            [
                (("a",), 1, {"sequence": 10}),
                (
                    ("c",),
                    1,
                    {
                        "sequence": 10,
                        "condition_field": "amount",
                        "operator": "gte",
                        "threshold": 1000,
                    },
                ),
            ]
        )
        self._run(
            category, "rule_adds_a_required_approver", request_vals={"amount": 5000}
        )

    def test_rule_below_its_threshold(self):
        category = self._amount_steps(
            [
                (("a",), 1, {"sequence": 10}),
                (
                    ("c",),
                    1,
                    {
                        "sequence": 10,
                        "condition_field": "amount",
                        "operator": "gte",
                        "threshold": 1000,
                    },
                ),
            ]
        )
        self._run(category, "rule_below_its_threshold", request_vals={"amount": 10})

    def test_band_replaces_the_approvers(self):
        # Each band is a step applicable over its own range.
        category = self._amount_steps(
            [
                (
                    ("a",),
                    1,
                    {"condition_field": "amount", "operator": "lt", "threshold": 1000},
                ),
                (
                    ("b",),
                    1,
                    {
                        "condition_field": "amount",
                        "operator": "between",
                        "threshold": 1000,
                        "threshold_max": 0,
                    },
                ),
            ]
        )
        self._run(
            category, "band_replaces_the_approvers", request_vals={"amount": 5000}
        )

    def test_a_figure_condition_needs_a_comparison(self):
        with self.assertRaises(ValidationError):
            self._amount_steps([(("a",), 1, {"condition_field": "amount"})])


@tagged("post_install", "-at_install")
class TestConvertedRoutingOutcomes(TestFlatRoutingOutcomes):
    """Every flat scenario, converted to steps first, reads as its flat script."""

    allow_inherited_tests_method = True

    def _run(
        self,
        category,
        script_name,
        request_vals=None,
        after_confirm=None,
        added_by_hand=(),
    ):
        category.action_convert_routing_to_steps()
        self.assertTrue(category.step_ids)
        self.assertFalse(category.approve_sequentially)
        self.assertFalse(
            category.rule_ids.filtered(
                lambda rule: (
                    rule.active
                    and rule.action_type in ("add_approver", "set_approvers")
                )
            )
        )

        def covered_by_steps(request):
            # Without a step, a request falls back to the flat approvers the
            # category still lists, which would hide a range the conversion missed.
            self.assertTrue(request._get_applicable_steps())
            if after_confirm:
                after_confirm(request)

        return super()._run(
            category, script_name, request_vals, covered_by_steps, added_by_hand
        )

    def test_a_configuration_steps_cannot_reproduce_is_refused(self):
        category = self._flat(
            [("a", False, 10), ("b", False, 20)],
            approval_minimum=1,
            has_amount="required",
        )
        for index in range(6):
            self.env["approval.rule"].create(
                {
                    "name": f"Adds {index}",
                    "category_id": category.id,
                    "condition_type": "threshold",
                    "condition_field": "amount",
                    "operator": "gte" if index % 2 else "lte",
                    "threshold": 1000 * (index + 1),
                    "action_type": "add_approver",
                    "approver_ids": [(6, 0, [self.people["c"].id])],
                }
            )
        self.assertIn("64 cases", category.steps_conversion_blockers)
        with self.assertRaisesRegex(UserError, "64 cases"):
            category.action_convert_routing_to_steps()
        self.assertFalse(category.step_ids)

    def test_a_convertible_category_says_nothing_against_it(self):
        category = self._flat([("a", False, 10)], approval_minimum=1)
        self.assertFalse(category.steps_conversion_blockers)


@tagged("post_install", "-at_install")
class TestConvertingEveryCategory(RoutingOutcomesCase):
    def _flat_category(self, **vals):
        return self._make_category(
            f"Every category {self._next_sequence_code()}",
            approvers=[(self.people["a"], False, 10), (self.people["b"], False, 20)],
            **vals,
        )

    def test_every_category_without_a_blocker_converts_and_the_rest_are_named(self):
        convertible = self._flat_category()
        blocked = self._flat_category(
            group_approval="exclusive",
            approver_group_id=self.pool.id,
            approve_sequentially=True,
        )
        result = self.env["approval.category"]._convert_every_category_to_steps()
        self.assertIn(convertible, result["converted"])
        self.assertTrue(convertible.step_ids)
        self.assertIn(blocked, result["blocked"])
        self.assertFalse(blocked.step_ids)
        self.assertNotIn(blocked, result["converted"])

    def test_every_category_a_module_ships_routes_by_steps_or_says_why(self):
        shipped = self.env["ir.model.data"].search(
            [("model", "=", "approval.category")]
        )
        categories = (
            self.env["approval.category"]
            .with_context(active_test=False)
            .browse(shipped.mapped("res_id"))
            .exists()
        )
        self.assertTrue(categories)
        on_their_list = categories.filtered(
            lambda category: (
                not category.step_ids and not category._get_steps_conversion_blockers()
            )
        )
        self.assertFalse(on_their_list.mapped("name"))

    def test_a_request_confirmed_on_the_list_keeps_routing_by_it(self):
        category = self._flat_category()
        category.approval_minimum = 2
        request = self._prepare_request(category)
        category.action_convert_routing_to_steps()
        # A live routing field: editing it extends the approvers of a pending request.
        request.priority = "1"
        request.invalidate_recordset()
        self.assertFalse(request.approver_ids.step_ids)
        self.assertFalse(request._get_applicable_steps())
        request.with_user(self.people["a"]).action_approve()
        self.assertEqual(request.state, "pending")
        request.with_user(self.people["b"]).action_approve()
        self.assertEqual(request.state, "approved")

    def test_a_request_confirmed_on_the_list_keeps_its_rule_approvers(self):
        category = self._flat_category(has_amount="required")
        self.env["approval.rule"].create(
            {
                "name": "Routing rule before the conversion",
                "category_id": category.id,
                "condition_type": "threshold",
                "condition_field": "amount",
                "operator": "gte",
                "threshold": 1000,
                "action_type": "add_approver",
                "approver_ids": [(6, 0, [self.people["c"].id])],
            }
        )
        request = self._prepare_request(category, amount=5000)
        self.assertIn(self.people["c"], request.approver_ids.user_id)
        category.action_convert_routing_to_steps()
        request.priority = "1"
        request.invalidate_recordset()
        self.assertIn(self.people["c"], request.approver_ids.user_id)
        request.with_user(self.people["a"]).action_approve()
        self.assertEqual(request.state, "pending")
        request.with_user(self.people["c"]).action_approve()
        self.assertEqual(request.state, "approved")

    def test_the_rules_steps_apply_by_stay_conditions(self):
        category = self._flat_category(has_amount="required", has_quantity="required")
        rules = self.env["approval.rule"]
        for field, threshold, user in (("amount", 1000, "c"), ("quantity", 5, "d")):
            rules |= self.env["approval.rule"].create(
                {
                    "name": f"Rule on {field}",
                    "category_id": category.id,
                    "condition_type": "threshold",
                    "condition_field": field,
                    "operator": "gte",
                    "threshold": threshold,
                    "action_type": "add_approver",
                    "approver_ids": [(6, 0, [self.people[user].id])],
                }
            )
        category.action_convert_routing_to_steps()
        self.assertEqual(len(category.step_ids), 4)
        self.assertEqual(set(rules.mapped("action_type")), {"condition"})
        self.assertTrue(all(rules.mapped("active")))
        with self.assertRaisesRegex(ValidationError, "apply by these rules"):
            rules[0].active = False
        with self.assertRaisesRegex(ValidationError, "apply by these rules"):
            rules[1].unlink()

    def test_a_rule_adding_approvers_is_refused_on_a_category_routed_by_steps(self):
        category = self._flat_category()
        category.action_convert_routing_to_steps()
        with self.assertRaisesRegex(ValidationError, "which read no rule"):
            self.env["approval.rule"].create(
                {
                    "name": "Late routing rule",
                    "category_id": category.id,
                    "condition_type": "threshold",
                    "condition_field": "amount",
                    "operator": "gte",
                    "threshold": 1000,
                    "action_type": "add_approver",
                    "approver_ids": [(6, 0, [self.people["c"].id])],
                }
            )

    def test_a_rule_left_beside_steps_becomes_a_step_of_its_approvers(self):
        category = self._flat_category(has_amount="required")
        rule = self.env["approval.rule"].create(
            {
                "name": "Rule beside steps",
                "category_id": category.id,
                "condition_type": "threshold",
                "condition_field": "amount",
                "operator": "gte",
                "threshold": 1000,
                "action_type": "add_approver",
                "approver_ids": [(6, 0, [self.people["c"].id])],
            }
        )
        self.env["approval.category.step"].create(
            {
                "category_id": category.id,
                "name": "Pool",
                "minimum": 1,
                "user_ids": [(6, 0, [self.people["a"].id, self.people["b"].id])],
            }
        )
        result = self.env[
            "approval.category"
        ]._route_rules_of_step_categories_by_steps()
        self.assertEqual(result["added"], rule)
        self.assertEqual(rule.action_type, "condition")
        above = self._prepare_request(category, amount=5000)
        above.with_user(self.people["a"]).action_approve()
        self.assertEqual(above.state, "pending")
        above.with_user(self.people["c"]).action_approve()
        self.assertEqual(above.state, "approved")
        below = self._prepare_request(category, amount=10)
        below.with_user(self.people["a"]).action_approve()
        self.assertEqual(below.state, "approved")

    def test_a_draft_raised_before_the_conversion_routes_by_the_steps(self):
        category = self._flat_category()
        request = self._prepare_request(category, confirm=False)
        category.action_convert_routing_to_steps()
        request.action_confirm()
        self.assertTrue(request.approver_ids.step_ids)

    def test_an_approver_list_line_is_refused_on_a_category_routed_by_steps(self):
        category = self._flat_category()
        category.action_convert_routing_to_steps()
        with self.assertRaisesRegex(ValidationError, "routes its requests by steps"):
            self.env["approval.category.approver"].create(
                {"category_id": category.id, "user_id": self.people["c"].id}
            )

    def test_adding_an_approver_follows_how_the_category_routes(self):
        flat = self._flat_category()
        flat._add_approver(self.people["c"], required=True)
        self.assertIn(self.people["c"], flat.approver_ids.user_id)

        stepped = self._flat_category()
        stepped.action_convert_routing_to_steps()
        stepped._add_approver(self.people["c"], required=True)
        member = stepped.step_ids.member_ids.filtered(
            lambda member: member.user_id == self.people["c"]
        )
        self.assertTrue(member.required)
        request = self._prepare_request(stepped)
        request.with_user(self.people["a"]).action_approve()
        self.assertEqual(request.state, "pending", "the required member still decides")
        request.with_user(self.people["c"]).action_approve()
        self.assertEqual(request.state, "approved")
