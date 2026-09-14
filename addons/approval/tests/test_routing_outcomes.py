from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import Form, tagged

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
    "owner_not_asked": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "approved", set(), set()),
    ],
    "rule_adds_a_required_approver": [
        (None, "pending", {"a", "c"}, {"a", "c"}),
        (("approve", "a"), "pending", {"c"}, {"c"}),
        (("approve", "c"), "approved", set(), set()),
    ],
    "rule_below_its_threshold": [
        (None, "pending", {"a"}, {"a"}),
        (("approve", "a"), "approved", set(), set()),
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
    approval activity. A category configured by an approver list and one configured
    by steps are each given the same scripts.
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
            self.env.invalidate_all()
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
        between=None,
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
            if between:
                between(request, index)
                request.invalidate_recordset()


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
        return self._stepped(steps)

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

    def _pool(self, approvers, **vals):
        return self._make_category(
            f"Pool routing {self._next_sequence_code()}",
            approvers=[
                (self.people[key], required, sequence)
                for key, required, sequence in approvers
            ],
            with_pool=True,
            **vals,
        )

    def test_group_asks_its_members(self):
        self._run(
            self._pool(
                [],
                approval_minimum=1,
                group_id=self.pool.id,
                asks_group_members=True,
            ),
            "group_asks_its_members",
        )

    def test_an_approver_added_by_hand_counts_toward_the_minimum(self):
        self._run(
            self._pool([("a", False, 10)], approval_minimum=2),
            "added_by_hand_counts",
            added_by_hand=["d"],
        )

    def test_a_category_whose_approvers_are_all_added_by_hand(self):
        self._run(
            self._pool([], approval_minimum=1),
            "only_added_by_hand",
            added_by_hand=["c", "d"],
        )

    def test_an_approver_added_by_hand_joins_a_sequence(self):
        self._run(
            self._pool(
                [("a", True, 10), ("b", True, 20)],
                approval_minimum=2,
                in_order=True,
            ),
            "added_by_hand_joins_the_sequence",
            added_by_hand=["d"],
        )

    def test_delegated_approver(self):
        category = self._pool([("a", False, 10), ("b", False, 20)], approval_minimum=1)

        def delegate_a_to_d(request):
            row = request.approver_ids.filtered(
                lambda approver: approver.user_id == self.people["a"]
            )
            self._delegate_row(row, self.people["d"])

        self._run(category, "delegated_approver", after_confirm=delegate_a_to_d)


@tagged("post_install", "-at_install")
class TestCategoriesRouteBySteps(RoutingOutcomesCase):
    def test_every_category_a_module_ships_routes_by_steps(self):
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
        self.assertFalse(
            categories.filtered(lambda category: not category.step_ids).mapped("name")
        )

    def test_a_category_created_from_the_configuration_routes_by_steps(self):
        categories = self.env["approval.category"].with_context(
            approval_category_routes_by_steps=True
        )
        with Form(categories) as form:
            form.name = f"Born with steps {self._next_sequence_code()}"
            form.sequence_code = self._next_sequence_code()
        category = form.record
        self.assertEqual(category.step_ids.mapped("counts_added_approvers"), [True])
        category.write(
            {
                name: "optional"
                for name, field in category._fields.items()
                if name.startswith("has_") and field.type == "selection"
            }
        )
        request = self._prepare_request(category, confirm=False)
        self.env["approval.approver"].create(
            {"request_id": request.id, "user_id": self.people["c"].id}
        )
        request.action_confirm()
        self.assertTrue(request.approver_ids.step_ids)
        request.with_user(self.people["c"]).action_approve()
        self.assertEqual(request.state, "approved")

    def test_adding_an_approver_joins_the_pool_step(self):
        category = self._make_category(
            f"Pool {self._next_sequence_code()}",
            approvers=[(self.people["a"], False, 10), (self.people["b"], False, 20)],
        )
        category._add_approver(self.people["c"], required=True)
        member = category.step_ids.member_ids.filtered(
            lambda member: member.user_id == self.people["c"]
        )
        self.assertTrue(member.required)
        request = self._prepare_request(category)
        request.with_user(self.people["a"]).action_approve()
        self.assertEqual(request.state, "pending", "the required member still decides")
        request.with_user(self.people["c"]).action_approve()
        self.assertEqual(request.state, "approved")

    def test_adding_an_approver_to_a_category_without_steps_creates_its_pool(self):
        category = self._make_category(
            f"No steps {self._next_sequence_code()}", approval_minimum=2
        )
        self.assertFalse(category.step_ids)
        category._add_approver(self.people["c"])
        self.assertEqual(category.step_ids.minimum, 2)
        self.assertTrue(category.step_ids.counts_added_approvers)
        self.assertEqual(category.step_ids.member_ids.user_id, self.people["c"])
