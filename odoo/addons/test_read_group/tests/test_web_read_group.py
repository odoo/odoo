from unittest.mock import patch

from odoo.tests import common


class TestWebReadGroup(common.TransactionCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        model_cls = type(self.env["base"])
        self._original_web_read_group = model_cls.web_read_group

        def _strip_version(records, *args, **kwargs):
            result = self._original_web_read_group(records, *args, **kwargs)
            if isinstance(result, dict):
                result.pop("__version", None)
            return result

        patcher = patch.object(model_cls, "web_read_group", _strip_version)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_version_key_present_and_stable(self):
        Model = self.env["test_read_group.aggregate"]
        Model.create({"key": 1, "value": 1})

        result = self._original_web_read_group(
            Model, domain=[], groupby=["key"], aggregates=["value:sum"]
        )
        self.assertIn("__version", result)
        version = result["__version"]
        self.assertIsInstance(version, str)
        self.assertTrue(version)

        result_again = self._original_web_read_group(
            Model, domain=[], groupby=["key"], aggregates=["value:sum"]
        )
        self.assertEqual(version, result_again["__version"])

        Model.create({"key": 2, "value": 2})
        result_changed = self._original_web_read_group(
            Model, domain=[], groupby=["key"], aggregates=["value:sum"]
        )
        self.assertNotEqual(version, result_changed["__version"])

    def test_limit_offset(self):
        Model = self.env["test_read_group.aggregate"]
        Model.create(
            [
                {"key": 1, "value": 1},
                {"key": 1, "value": 2},
                {"key": 1, "value": 3},
                {"key": 2, "value": 4},
                {"key": 2},
                {"key": 2, "value": 5},
                {},
                {"value": 6},
            ],
        )

        Model.web_read_group(domain=[], groupby=["key"], aggregates=["value:sum"])

        with self.assertQueryCount(1):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    limit=4,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("key", "=", 1)],
                            "key": 1,
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                        },
                        {
                            "__extra_domain": [("key", "=", 2)],
                            "key": 2,
                            "__count": 3,
                            "value:sum": 4 + 5,
                        },
                        {
                            "__extra_domain": [("key", "=", False)],
                            "key": False,
                            "__count": 2,
                            "value:sum": 6,
                        },
                    ],
                    "length": 3,
                },
            )

        with self.assertQueryCount(2):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    limit=2,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("key", "=", 1)],
                            "key": 1,
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                        },
                        {
                            "__extra_domain": [("key", "=", 2)],
                            "key": 2,
                            "__count": 3,
                            "value:sum": 4 + 5,
                        },
                    ],
                    "length": 3,
                },
            )

        with self.assertQueryCount(1):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    offset=1,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("key", "=", 2)],
                            "key": 2,
                            "__count": 3,
                            "value:sum": 4 + 5,
                        },
                        {
                            "__extra_domain": [("key", "=", False)],
                            "key": False,
                            "__count": 2,
                            "value:sum": 6,
                        },
                    ],
                    "length": 3,
                },
            )

        with self.assertQueryCount(2):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    offset=1,
                    limit=2,
                    order="key DESC",
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("key", "=", 2)],
                            "key": 2,
                            "__count": 3,
                            "value:sum": 4 + 5,
                        },
                        {
                            "__extra_domain": [("key", "=", 1)],
                            "key": 1,
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                        },
                    ],
                    "length": 3,
                },
            )

    @patch("odoo.addons.web.models.web_read_group.MAX_NUMBER_OPENED_GROUPS", 2)
    def test_auto_unfold_limit(self):
        Model = self.env["test_read_group.aggregate"]
        records = Model.create(
            [
                {"key": 1, "value": 1},
                {"key": 1, "value": 2},
                {"key": 1, "value": 3},
                {"key": 2, "value": 4},
                {"key": 2},
                {"key": 2, "value": 5},
                {},
                {"value": 6},
            ],
        )

        read_spec = {
            "key": {},
            "value": {},
        }
        key1_read_records = records[:3].web_read(read_spec)
        key2_read_records = records[3:6].web_read(read_spec)

        Model.web_read_group(
            domain=[],
            groupby=["key"],
            aggregates=["value:sum"],
            auto_unfold=True,
            unfold_read_specification=read_spec,
        )

        self.env.invalidate_all()

        with self.assertQueryCount(3):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    auto_unfold=True,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("key", "=", 1)],
                            "key": 1,
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                            "__records": key1_read_records,
                        },
                        {
                            "__extra_domain": [("key", "=", 2)],
                            "key": 2,
                            "__count": 3,
                            "value:sum": 4 + 5,
                            "__records": key2_read_records,
                        },
                        {
                            "__extra_domain": [("key", "=", False)],
                            "key": False,
                            "__count": 2,
                            "value:sum": 6,
                        },
                    ],
                    "length": 3,
                },
            )

        self.env.invalidate_all()

        with self.assertQueryCount(3):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    auto_unfold=True,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("key", "=", 1)],
                            "key": 1,
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                            "__records": key1_read_records,
                        },
                        {
                            "__extra_domain": [("key", "=", 2)],
                            "key": 2,
                            "__count": 3,
                            "value:sum": 4 + 5,
                            "__records": key2_read_records,
                        },
                        {
                            "__extra_domain": [("key", "=", False)],
                            "key": False,
                            "__count": 2,
                            "value:sum": 6,
                        },
                    ],
                    "length": 3,
                },
            )

        self.env.invalidate_all()

        with self.assertQueryCount(4):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    offset=1,
                    limit=1,
                    auto_unfold=True,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("key", "=", 2)],
                            "key": 2,
                            "__count": 3,
                            "value:sum": 4 + 5,
                            "__records": key2_read_records,
                        },
                    ],
                    "length": 3,
                },
            )

    def test_unfolded_specific_groups(self):
        Model = self.env["test_read_group.aggregate"]
        partner_1, partner_2 = self.env["res.partner"].create(
            [
                {"name": "P1"},
                {"name": "P2"},
            ],
        )
        records = Model.create(
            [
                {"partner_id": partner_1.id, "key": 1, "value": 1},
                {"partner_id": partner_1.id, "key": 1, "value": 2},
                {"partner_id": partner_1.id, "key": 1, "value": 3},
                {"partner_id": partner_2.id, "key": 1, "value": 4},
                {"partner_id": partner_2.id, "key": 2},
                {"partner_id": partner_2.id, "value": 5},
                {},
                {"value": 6},
            ],
        )

        read_spec = {
            "key": {},
            "value": {},
            "partner_id": {"fields": {"display_name": {}}},
        }

        Model.web_read_group(
            domain=[],
            groupby=["partner_id", "key"],
            aggregates=["value:sum"],
        )

        self.env.invalidate_all()

        with self.assertQueryCount(2):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["partner_id", "key"],
                    aggregates=["value:sum"],
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("partner_id", "=", partner_1.id)],
                            "partner_id": (partner_1.id, "P1"),
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                        },
                        {
                            "__extra_domain": [("partner_id", "=", partner_2.id)],
                            "partner_id": (partner_2.id, "P2"),
                            "__count": 3,
                            "value:sum": 4 + 5,
                        },
                        {
                            "__extra_domain": [("partner_id", "=", False)],
                            "partner_id": False,
                            "__count": 2,
                            "value:sum": 6,
                        },
                    ],
                    "length": 3,
                },
            )

        opening_info = [
            {
                "value": partner_1.id,
                "folded": False,
                "limit": 2,
                "offset": 0,
                "progressbar_domain": [],
                "groups": [
                    {
                        "value": 1,
                        "folded": False,
                        "limit": 2,
                        "offset": 2,
                        "progressbar_domain": [],
                    },
                ],
            },
            {
                "value": partner_2.id,
                "folded": False,
                "limit": 2,
                "offset": 2,
                "groups": [
                    {
                        "value": False,
                        "folded": False,
                        "limit": 2,
                        "offset": 0,
                        "progressbar_domain": [],
                    },
                ],
            },
            {
                "value": False,
                "folded": True,
            },
        ]
        read_record_2 = records[2].web_read(read_spec)
        read_record_5 = records[5].web_read(read_spec)

        self.env.invalidate_all()

        with self.assertQueryCount(6):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["partner_id", "key"],
                    aggregates=["value:sum"],
                    opening_info=opening_info,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("partner_id", "=", partner_1.id)],
                            "partner_id": (partner_1.id, "P1"),
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                            "__groups": {
                                "groups": [
                                    {
                                        "__extra_domain": [("key", "=", 1)],
                                        "key": 1,
                                        "__count": 3,
                                        "value:sum": 1 + 2 + 3,
                                        "__records": read_record_2,
                                    },
                                ],
                                "length": 1,
                            },
                        },
                        {
                            "__extra_domain": [("partner_id", "=", partner_2.id)],
                            "partner_id": (partner_2.id, "P2"),
                            "__count": 3,
                            "value:sum": 4 + 5,
                            "__groups": {
                                "groups": [
                                    {
                                        "key": False,
                                        "__extra_domain": [("key", "=", False)],
                                        "value:sum": 5,
                                        "__count": 1,
                                        "__records": read_record_5,
                                    }
                                ],
                                "length": 3,
                            },
                        },
                        {
                            "__extra_domain": [("partner_id", "=", False)],
                            "partner_id": False,
                            "__count": 2,
                            "value:sum": 6,
                        },
                    ],
                    "length": 3,
                },
            )

    def test_auto_unfolded(self):
        Model = self.env["test_read_group.aggregate"]
        partner_1, partner_2 = self.env["res.partner"].create(
            [
                {"name": "P1"},
                {"name": "P2"},
            ],
        )
        records = Model.create(
            [
                {"partner_id": partner_1.id, "key": 1, "value": 1},
                {"partner_id": partner_1.id, "key": 1, "value": 2},
                {"partner_id": partner_1.id, "key": 1, "value": 3},
                {"partner_id": partner_2.id, "key": 1, "value": 4},
                {"partner_id": partner_2.id, "key": 2},
                {"partner_id": partner_2.id, "value": 5},
                {},
                {"value": 6},
            ],
        )

        read_spec = {
            "key": {},
            "value": {},
            "partner_id": {"fields": {"display_name": {}}},
        }

        Model.web_read_group(
            domain=[],
            groupby=["partner_id"],
            aggregates=["value:sum"],
            auto_unfold=True,
            unfold_read_specification=read_spec,
        )
        self.env.invalidate_all()

        with self.assertQueryCount(4):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["partner_id"],
                    aggregates=["value:sum"],
                    auto_unfold=True,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("partner_id", "=", partner_1.id)],
                            "partner_id": (partner_1.id, "P1"),
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                            "__records": records[:3].web_read(read_spec),
                        },
                        {
                            "__extra_domain": [("partner_id", "=", partner_2.id)],
                            "partner_id": (partner_2.id, "P2"),
                            "__count": 3,
                            "value:sum": 4 + 5,
                            "__records": records[3:6].web_read(read_spec),
                        },
                        {
                            "__extra_domain": [("partner_id", "=", False)],
                            "partner_id": False,
                            "__count": 2,
                            "value:sum": 6,
                        },
                    ],
                    "length": 3,
                },
            )

        self.env.invalidate_all()

        with self.assertQueryCount(4):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["partner_id", "key"],
                    aggregates=["value:sum"],
                    auto_unfold=True,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("partner_id", "=", partner_1.id)],
                            "partner_id": (partner_1.id, "P1"),
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                            "__groups": {
                                "groups": [
                                    {
                                        "__extra_domain": [("key", "=", 1)],
                                        "key": 1,
                                        "__count": 3,
                                        "value:sum": 1 + 2 + 3,
                                    },
                                ],
                                "length": 1,
                            },
                        },
                        {
                            "__extra_domain": [("partner_id", "=", partner_2.id)],
                            "partner_id": (partner_2.id, "P2"),
                            "__count": 3,
                            "value:sum": 4 + 5,
                            "__groups": {
                                "groups": [
                                    {
                                        "__extra_domain": [("key", "=", 1)],
                                        "key": 1,
                                        "__count": 1,
                                        "value:sum": 4,
                                    },
                                    {
                                        "__extra_domain": [("key", "=", 2)],
                                        "key": 2,
                                        "__count": 1,
                                        "value:sum": False,
                                    },
                                    {
                                        "__extra_domain": [("key", "=", False)],
                                        "key": False,
                                        "__count": 1,
                                        "value:sum": 5,
                                    },
                                ],
                                "length": 3,
                            },
                        },
                        {
                            "__extra_domain": [("partner_id", "=", False)],
                            "partner_id": False,
                            "__count": 2,
                            "value:sum": 6,
                        },
                    ],
                    "length": 3,
                },
            )

    def test_extra_domain_records(self):

        Model = self.env["test_read_group.aggregate"]
        records = Model.create(
            [
                {"key": 1, "value": 1},
                {"key": 1, "value": 2},
                {"key": 1, "value": 3},
                {"key": 2, "value": 4},
                {"key": 2},
                {"key": 2, "value": 5},
                {},
                {"value": 6},
            ],
        )

        opening_info = [
            {
                "value": 1,
                "folded": False,
                "limit": 2,
                "offset": 0,
                "progressbar_domain": [
                    ["value", "=", 1],
                ],
            },
            {
                "value": 2,
                "folded": False,
                "limit": 2,
                "offset": 0,
                "progressbar_domain": [
                    ["value", "=", 5],
                ],
            },
            {
                "value": False,
                "folded": True,
            },
        ]

        read_spec = {"value": {}}

        Model.web_read_group(
            domain=[],
            groupby=["key"],
            aggregates=["value:sum"],
            auto_unfold=True,
            opening_info=opening_info,
            unfold_read_specification=read_spec,
            unfold_read_default_limit=80,
        )

        self.env.invalidate_all()

        with self.assertQueryCount(5):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    auto_unfold=True,
                    opening_info=opening_info,
                    unfold_read_specification=read_spec,
                    unfold_read_default_limit=80,
                ),
                {
                    "groups": [
                        {
                            "key": 1,
                            "__extra_domain": [("key", "=", 1)],
                            "value:sum": 1,
                            "__count": 3,
                            "__records": records[0].web_read(read_spec),
                        },
                        {
                            "key": 2,
                            "__extra_domain": [("key", "=", 2)],
                            "value:sum": 5,
                            "__count": 3,
                            "__records": records[5].web_read(read_spec),
                        },
                        {
                            "key": False,
                            "__extra_domain": [("key", "=", False)],
                            "value:sum": 6,
                            "__count": 2,
                        },
                    ],
                    "length": 3,
                },
            )

    @patch("odoo.addons.web.models.web_read_group.MAX_NUMBER_OPENED_GROUPS", 1)
    def test_specific_opened_group_and_unfold_limit(self):
        Model = self.env["test_read_group.aggregate"]
        records = Model.create(
            [
                {"key": 1, "value": 1},
                {"key": 1, "value": 2},
                {"key": 1, "value": 3},
                {"key": 2, "value": 4},
                {"key": 2},
                {"key": 2, "value": 5},
                {},
                {"value": 6},
            ],
        )

        opening_info = [
            {
                "value": 1,
                "folded": False,
                "limit": 2,
                "offset": 0,
                "progressbar_domain": [],
            },
            {
                "value": 2,
                "folded": True,
            },
            {
                "value": False,
                "folded": False,
                "limit": 2,
                "offset": 0,
                "progressbar_domain": [],
            },
        ]

        read_spec = {"value": {}}

        Model.web_read_group(
            domain=[],
            groupby=["key"],
            aggregates=["value:sum"],
            auto_unfold=True,
            opening_info=opening_info,
            unfold_read_specification=read_spec,
        )

        self.env.invalidate_all()

        with self.assertQueryCount(3):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    auto_unfold=True,
                    opening_info=opening_info,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "key": 1,
                            "__extra_domain": [("key", "=", 1)],
                            "value:sum": 6,
                            "__count": 3,
                            "__records": records[:2].web_read(read_spec),
                        },
                        {
                            "key": 2,
                            "__extra_domain": [("key", "=", 2)],
                            "value:sum": 9,
                            "__count": 3,
                        },
                        {
                            "key": False,
                            "__extra_domain": [("key", "=", False)],
                            "value:sum": 6,
                            "__count": 2,
                            "__records": records[-2:].web_read(read_spec),
                        },
                    ],
                    "length": 3,
                },
            )

    def test_auto_fold_info(self):
        order_1, order_2, order_3, order_4 = self.env["test_read_group.order"].create(
            [
                {"name": "O1", "fold": False},
                {"name": "O2", "fold": True},
                {"name": "O3 empty", "fold": False},
                {"name": "O4 empty", "fold": True},
            ]
        )
        Line = self.env["test_read_group.order.line"].with_context(
            read_group_expand=True
        )
        records = Line.create(
            [
                {"order_expand_id": order_1.id, "value": 1},
                {"order_expand_id": order_2.id, "value": 2},
                {"order_expand_id": order_2.id, "value": 2},
                {"order_expand_id": False, "value": 3},
            ]
        )

        read_spec = {"value": {}}

        Line.web_read_group(
            domain=[],
            groupby=["order_expand_id"],
            aggregates=["value:sum"],
            auto_unfold=True,
            unfold_read_specification=read_spec,
        )

        self.env.invalidate_all()

        with self.assertQueryCount(5):
            self.assertEqual(
                Line.web_read_group(
                    domain=[],
                    groupby=["order_expand_id"],
                    aggregates=["value:sum"],
                    auto_unfold=True,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "order_expand_id": (order_1.id, "O1"),
                            "__extra_domain": [("order_expand_id", "=", order_1.id)],
                            "value:sum": 1,
                            "__count": 1,
                            "__records": records[0].web_read(read_spec),
                        },
                        {
                            "order_expand_id": (order_2.id, "O2"),
                            "__extra_domain": [("order_expand_id", "=", order_2.id)],
                            "value:sum": 4,
                            "__count": 2,
                        },
                        {
                            "order_expand_id": (order_3.id, "O3 empty"),
                            "__extra_domain": [("order_expand_id", "=", order_3.id)],
                            "value:sum": False,
                            "__count": 0,
                            "__records": [],
                        },
                        {
                            "order_expand_id": (order_4.id, "O4 empty"),
                            "__extra_domain": [("order_expand_id", "=", order_4.id)],
                            "value:sum": False,
                            "__count": 0,
                        },
                        {
                            "order_expand_id": False,
                            "__extra_domain": [("order_expand_id", "=", False)],
                            "value:sum": 3,
                            "__count": 1,
                        },
                    ],
                    "length": 5,
                },
            )

        self.env.invalidate_all()

        with self.assertQueryCount(5):
            self.assertEqual(
                Line.web_read_group(
                    domain=[],
                    groupby=["order_expand_id", "value"],
                    aggregates=[],
                    auto_unfold=True,
                    unfold_read_specification=read_spec,
                ),
                {
                    "groups": [
                        {
                            "order_expand_id": (order_1.id, "O1"),
                            "__extra_domain": [("order_expand_id", "=", order_1.id)],
                            "__count": 1,
                            "__groups": {
                                "groups": [
                                    {
                                        "value": 1,
                                        "__extra_domain": [("value", "=", 1)],
                                        "__count": 1,
                                    },
                                ],
                                "length": 1,
                            },
                        },
                        {
                            "order_expand_id": (order_2.id, "O2"),
                            "__extra_domain": [("order_expand_id", "=", order_2.id)],
                            "__count": 2,
                        },
                        {
                            "order_expand_id": (order_3.id, "O3 empty"),
                            "__extra_domain": [("order_expand_id", "=", order_3.id)],
                            "__count": 0,
                            "__groups": {
                                "groups": [],
                                "length": 0,
                            },
                        },
                        {
                            "order_expand_id": (order_4.id, "O4 empty"),
                            "__extra_domain": [("order_expand_id", "=", order_4.id)],
                            "__count": 0,
                        },
                        {
                            "order_expand_id": False,
                            "__extra_domain": [("order_expand_id", "=", False)],
                            "__count": 1,
                        },
                    ],
                    "length": 5,
                },
            )

    def test_order(self):
        Model = self.env["test_read_group.aggregate"]
        records = Model.create(
            [
                {"key": 1, "value": 1},
                {"key": 1, "value": 2},
                {"key": 1, "value": 3},
                {"key": 2, "value": 4},
                {"key": 2, "value": 0},
                {"key": 2, "value": 5},
                {"value": 0},
                {"value": 6},
            ],
        )

        read_spec = {
            "key": {},
            "value": {},
        }
        key1_read_records = records[:3].web_read(read_spec)
        key2_read_records = records[3:6].web_read(read_spec)
        key_false_read_records = records[6:].web_read(read_spec)
        Model.web_read_group(
            domain=[],
            groupby=["key"],
            aggregates=["value:sum"],
            unfold_read_specification=read_spec,
        )

        with self.assertQueryCount(2):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["key"],
                    aggregates=["value:sum"],
                    unfold_read_specification=read_spec,
                    auto_unfold=True,
                    order="__count",
                ),
                {
                    "groups": [
                        {
                            "key": False,
                            "__extra_domain": [("key", "=", False)],
                            "value:sum": 6,
                            "__count": 2,
                            "__records": key_false_read_records,
                        },
                        {
                            "key": 1,
                            "__extra_domain": [("key", "=", 1)],
                            "value:sum": 6,
                            "__count": 3,
                            "__records": key1_read_records,
                        },
                        {
                            "key": 2,
                            "__extra_domain": [("key", "=", 2)],
                            "value:sum": 9,
                            "__count": 3,
                            "__records": key2_read_records,
                        },
                    ],
                    "length": 3,
                },
            )

        self.assertEqual(
            Model.web_read_group(
                domain=[],
                groupby=["key"],
                aggregates=["value:sum"],
                unfold_read_specification=read_spec,
                auto_unfold=True,
                order="__count DESC, key DESC",
            ),
            {
                "groups": [
                    {
                        "key": 2,
                        "__extra_domain": [("key", "=", 2)],
                        "value:sum": 9,
                        "__count": 3,
                        "__records": key2_read_records,
                    },
                    {
                        "key": 1,
                        "__extra_domain": [("key", "=", 1)],
                        "value:sum": 6,
                        "__count": 3,
                        "__records": key1_read_records,
                    },
                    {
                        "key": False,
                        "__extra_domain": [("key", "=", False)],
                        "value:sum": 6,
                        "__count": 2,
                        "__records": key_false_read_records,
                    },
                ],
                "length": 3,
            },
        )

        self.assertEqual(
            Model.web_read_group(
                domain=[],
                groupby=["key"],
                aggregates=["value:sum"],
                unfold_read_specification=read_spec,
                auto_unfold=True,
                order="value",
            ),
            {
                "groups": [
                    {
                        "key": 1,
                        "__extra_domain": [("key", "=", 1)],
                        "value:sum": 6,
                        "__count": 3,
                        "__records": sorted(
                            key1_read_records, key=lambda r: r["value"]
                        ),
                    },
                    {
                        "key": False,
                        "__extra_domain": [("key", "=", False)],
                        "value:sum": 6,
                        "__count": 2,
                        "__records": sorted(
                            key_false_read_records, key=lambda r: r["value"]
                        ),
                    },
                    {
                        "key": 2,
                        "__extra_domain": [("key", "=", 2)],
                        "value:sum": 9,
                        "__count": 3,
                        "__records": sorted(
                            key2_read_records, key=lambda r: r["value"]
                        ),
                    },
                ],
                "length": 3,
            },
        )

        self.assertEqual(
            Model.web_read_group(
                domain=[],
                groupby=["key"],
                aggregates=["value:sum"],
                unfold_read_specification=read_spec,
                auto_unfold=True,
                order="key DESC",
            ),
            {
                "groups": [
                    {
                        "key": False,
                        "__extra_domain": [("key", "=", False)],
                        "value:sum": 6,
                        "__count": 2,
                        "__records": key_false_read_records,
                    },
                    {
                        "key": 2,
                        "__extra_domain": [("key", "=", 2)],
                        "value:sum": 9,
                        "__count": 3,
                        "__records": key2_read_records,
                    },
                    {
                        "key": 1,
                        "__extra_domain": [("key", "=", 1)],
                        "value:sum": 6,
                        "__count": 3,
                        "__records": key1_read_records,
                    },
                ],
                "length": 3,
            },
        )

    def test_read_extra_info_groupby_value(self):
        Model = self.env["test_read_group.aggregate"]
        partner_1, partner_2 = self.env["res.partner"].create(
            [
                {"name": "P1", "ref": "P1-REF"},
                {"name": "P2", "ref": "P2-REF"},
            ],
        )
        Model.create(
            [
                {"partner_id": partner_1.id, "key": 1, "value": 1},
                {"partner_id": partner_1.id, "key": 1, "value": 2},
                {"partner_id": partner_1.id, "key": 1, "value": 3},
                {"partner_id": partner_2.id, "key": 1, "value": 4},
                {"partner_id": partner_2.id, "key": 2},
                {"partner_id": partner_2.id, "value": 5},
                {},
                {"value": 6},
            ],
        )

        Model.web_read_group(
            domain=[],
            groupby=["partner_id"],
            aggregates=["value:sum"],
            groupby_read_specification={"partner_id": {"ref": {}}},
        )
        self.env.invalidate_all()

        Partner = self.registry["res.partner"]
        with (
            self.assertQueryCount(2),
            patch.object(
                Partner,
                "web_read",
                autospec=True,
                side_effect=Partner.web_read,
            ) as spy_web_read,
        ):
            self.assertEqual(
                Model.web_read_group(
                    domain=[],
                    groupby=["partner_id"],
                    aggregates=["value:sum"],
                    groupby_read_specification={"partner_id": {"ref": {}}},
                ),
                {
                    "groups": [
                        {
                            "__extra_domain": [("partner_id", "=", partner_1.id)],
                            "partner_id": (partner_1.id, "P1"),
                            "__count": 3,
                            "value:sum": 1 + 2 + 3,
                            "__values": {"id": partner_1.id, "ref": "P1-REF"},
                        },
                        {
                            "__extra_domain": [("partner_id", "=", partner_2.id)],
                            "partner_id": (partner_2.id, "P2"),
                            "__count": 3,
                            "value:sum": 4 + 5,
                            "__values": {"id": partner_2.id, "ref": "P2-REF"},
                        },
                        {
                            "__extra_domain": [("partner_id", "=", False)],
                            "partner_id": False,
                            "__count": 2,
                            "value:sum": 6,
                            "__values": {"id": False},
                        },
                    ],
                    "length": 3,
                },
            )

            self.assertEqual(spy_web_read.call_count, 1)
