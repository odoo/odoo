from odoo import Command, fields
from odoo.tests import common


class TestStandInFields(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = cls.env["test_read_group.user"]
        cls.ann, cls.bob = User.create([{"name": "Ann"}, {"name": "Bob"}])
        cls.Task = cls.env["test_read_group.task"]
        cls.tasks = cls.Task.create(
            [
                {
                    "name": "a",
                    "key": "x",
                    "ref": "9",
                    "integer": 1,
                    "user_ids": [Command.set(cls.ann.ids)],
                },
                {
                    "name": "b",
                    "key": "x",
                    "ref": "10",
                    "integer": 2,
                    "user_ids": [Command.set(cls.bob.ids)],
                },
                {
                    "name": "c",
                    "key": "y",
                    "ref": "8",
                    "integer": 4,
                    "user_ids": [Command.set(cls.ann.ids)],
                },
                {"name": "d", "key": "y", "ref": "11", "integer": 8},
            ]
        )
        cls.domain = [("id", "in", cls.tasks.ids)]

    def test_a_groupby_on_the_field_groups_through_its_stand_in(self):
        through = self.Task._read_group(
            self.domain,
            ["lead_user_id"],
            ["__count", "integer:sum"],
            order="lead_user_id",
        )
        direct = self.Task._read_group(
            self.domain, ["user_ids"], ["__count", "integer:sum"], order="user_ids"
        )
        self.assertEqual(through, direct)
        self.assertEqual(
            [(user, count) for user, count, _total in through],
            [(self.ann, 2), (self.bob, 1), (self.env["test_read_group.user"], 1)],
        )

    def test_the_groupby_name_orders_its_groups(self):
        groups = self.Task._read_group(
            self.domain, ["lead_user_id"], ["__count"], order="lead_user_id desc"
        )
        self.assertEqual(
            [user for user, _count in groups],
            [self.env["test_read_group.user"], self.bob, self.ann],
        )

    def test_a_many2one_stand_in_orders_its_groups_by_the_comodel_order(self):
        Order = self.env["test_read_group.order"]
        orders = Order.create(
            [
                {"name": "first", "company_dependent_name": "b"},
                {"name": "second", "company_dependent_name": "a"},
            ]
        )
        Line = self.env["test_read_group.order.line"].with_context(
            test_read_group_order_company_dependent=True
        )
        lines = Line.create(
            [
                {"order_id": orders[0].id, "value": 1},
                {"order_id": orders[1].id, "value": 2},
            ]
        )
        domain = [("id", "in", lines.ids)]
        through = Line._read_group(
            domain, ["current_order_id"], ["value:sum"], order="current_order_id"
        )
        direct = Line._read_group(domain, ["order_id"], ["value:sum"], order="order_id")
        self.assertEqual(through, direct)
        self.assertEqual([order for order, _total in through], [orders[1], orders[0]])

    def test_a_many2one_stand_in_follows_a_static_comodel_order(self):
        Partner = self.env["res.partner"]
        zed, abe = Partner.create([{"name": "Zed Stand-in"}, {"name": "Abe Stand-in"}])
        Aggregate = self.env["test_read_group.aggregate"]
        records = Aggregate.create(
            [
                {"partner_id": zed.id, "value": 1},
                {"partner_id": abe.id, "value": 2},
                {"value": 4},
            ]
        )
        domain = [("id", "in", records.ids)]
        for order in ("customer_id", "customer_id desc", None):
            with self.subTest(order=order):
                through = Aggregate._read_group(
                    domain, ["customer_id"], ["value:sum"], order=order
                )
                direct = Aggregate._read_group(
                    domain,
                    ["partner_id"],
                    ["value:sum"],
                    order=order and order.replace("customer_id", "partner_id"),
                )
                self.assertEqual(through, direct)
        self.assertEqual(
            [
                partner
                for partner, _total in Aggregate._read_group(
                    domain, ["customer_id"], ["value:sum"], order="customer_id"
                )
            ][:2],
            [abe, zed],
        )

    def test_grouping_sets_treat_the_field_as_the_many2many_it_groups_through(self):
        grouping_sets = [["lead_user_id"], ["key"], []]
        through = self.Task._read_grouping_sets(
            self.domain,
            grouping_sets,
            ["__count", "integer:sum"],
            order="lead_user_id, key",
        )
        direct = self.Task._read_grouping_sets(
            self.domain,
            [["user_ids"], ["key"], []],
            ["__count", "integer:sum"],
            order="user_ids, key",
        )
        self.assertEqual(through, direct)
        self.assertEqual(through[2], [(4, 15)])

    def test_web_groups_keep_the_name_the_view_asked_for(self):
        groups = self.Task.formatted_read_group(
            self.domain, ["lead_user_id"], ["__count"]
        )
        self.assertEqual(
            [group["lead_user_id"] for group in groups],
            [(self.ann.id, "Ann"), (self.bob.id, "Bob"), False],
        )
        self.assertEqual(
            groups[0]["__extra_domain"], [("lead_user_id", "=", self.ann.id)]
        )

    def test_an_order_on_the_field_sorts_by_its_stand_in(self):
        self.assertEqual(
            self.Task.search(self.domain, order="ref desc").ids,
            self.Task.search(self.domain, order="id desc").ids,
        )
        self.assertEqual(
            self.Task.search(self.domain, order="key, ref").ids,
            self.Task.search(self.domain, order="key, id").ids,
        )
        self.assertNotEqual(
            self.tasks.sorted("ref").ids,
            self.Task.search(self.domain, order="ref").ids,
            "the char values sort differently, so the order really comes from id",
        )

    def test_a_stand_in_that_does_not_fit_is_refused_at_setup(self):
        cases = [
            (
                fields.Many2one("test_read_group.user", group_by_field="nope"),
                "names no other field",
            ),
            (
                fields.Many2one("test_read_group.user", group_by_field="tag_ids"),
                "groups other values",
            ),
            (fields.Char(group_by_field="integer"), "groups other values"),
            (fields.Char(order_by_field="nope"), "names no other field"),
        ]
        for field, message in cases:
            field._setup_attrs__(type(self.Task), "probe_field")
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(ValueError, message),
            ):
                field._check_stand_in_fields(self.Task)

    def test_a_groupby_on_a_sql_hooked_field_groups_by_its_expression(self):
        groups = self.Task._read_group(
            self.domain, ["parity"], ["__count", "id:array_agg"], order="parity"
        )
        by_python = {}
        for task in self.tasks:
            by_python.setdefault(task.parity, []).append(task.id)
        self.assertEqual(
            [(parity, count, sorted(ids)) for parity, count, ids in groups],
            [
                ("even", 3, sorted(by_python["even"])),
                ("odd", 1, sorted(by_python["odd"])),
            ],
        )

    def test_an_order_on_a_sql_hooked_field_sorts_by_its_expression(self):
        ordered = self.Task.search(self.domain, order="parity desc, integer")
        self.assertEqual(ordered.mapped("parity"), ["odd", "even", "even", "even"])
        self.assertEqual(ordered.mapped("integer"), [1, 2, 4, 8])
        self.assertTrue(self.Task._is_field_sortable("parity"))

    def test_a_grouped_order_on_a_sql_hooked_field_orders_the_groups(self):
        groups = self.Task._read_group(
            self.domain, ["parity"], ["__count"], order="parity desc"
        )
        self.assertEqual([parity for parity, _count in groups], ["odd", "even"])

    def test_a_sql_hook_that_names_no_method_is_refused_at_setup(self):
        cases = [
            (fields.Char(group_by_sql="_nope"), "names no method"),
            (fields.Char(order_by_sql="_nope"), "names no method"),
            (
                fields.Char(group_by_sql="_parity_group_sql", group_by_field="key"),
                "cannot both be set",
            ),
        ]
        for field, message in cases:
            field._setup_attrs__(type(self.Task), "probe_field")
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(ValueError, message),
            ):
                field._check_stand_in_fields(self.Task)

    def test_a_field_composing_its_own_sql_orders_groups_and_aggregates(self):
        ordered = self.Task.search(self.domain, order="integer_squared desc")
        self.assertEqual(ordered.mapped("integer"), [8, 4, 2, 1])
        self.assertTrue(self.Task._is_field_sortable("integer_squared"))
        groups = self.Task._read_group(
            self.domain, ["integer_squared"], ["__count"], order="integer_squared"
        )
        self.assertEqual(groups, [(1, 1), (4, 1), (16, 1), (64, 1)])
        [(total,)] = self.Task._read_group(self.domain, [], ["integer_squared:sum"])
        self.assertEqual(total, 85)

    def test_a_value_sql_hook_that_names_no_method_is_refused_at_setup(self):
        field = fields.Char(value_sql="_nope")
        field._setup_attrs__(type(self.Task), "probe_field")
        with self.assertRaisesRegex(ValueError, "names no method"):
            field._check_stand_in_fields(self.Task)
