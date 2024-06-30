from odoo.tests import common


class TestRelatedReadGroup(common.TransactionCase):
    def test_read_group_unity_kanban(self):
        pass

    def test_read_group_unity_two_level(self):
        records = self.env["test_read_group.aggregate"].create(
            [
                {"key": 0, "value": 0, "numeric_value": 1.0},
                {"key": 0, "value": 0, "numeric_value": 2.0},
                {"key": 0, "value": 1, "numeric_value": 3.0},
                {"key": 0, "value": 2, "numeric_value": 4.0},
                {"key": 1, "value": 0, "numeric_value": 5.0},
                {"key": 1, "value": 1, "numeric_value": 6.0},
                {"key": 1, "value": 1, "numeric_value": 7.0},
                {"key": 2, "value": 1, "numeric_value": 8.0},
                {"key": 2, "value": 1, "numeric_value": 9.0},
            ]
        )

        # First call list view
        self.env["test_read_group.aggregate"].web_read_group_unity(
            [("id", "in", records.ids)],
            ["key"],
            ["__count", "numeric_value:sum"],
            extra_order="numeric_value",
            limit=80,
            offset=0,
            open_auto=0,  # No expand
            open_groups=[],
            search_read_specification={"key": {}, "value": {}, "numeric_value": {}},
            search_limit=80,
        )

        # Poeple use a little bit the list view:
        # - Open group of (key=0)
        # - Open group of (key=1)
        # - Open group of (key=0, value=0)
        # - Open group of (key=0, value=1)
        # - Open group of (key=1, value=1)

        res = self.env["test_read_group.aggregate"].web_read_group_unity(
            [("id", "in", records.ids)],
            ["key", "value"],
            ["__count", "numeric_value:sum"],
            extra_order="numeric_value",
            limit=80,
            offset=0,
            open_auto=0,  # No expand
            open_groups=[[0], [1], [0, 0], [0, 1], [1, 1]],
            search_read_specification={"numeric_value": {}},
            search_limit=80,
        )
        excepted_result = {
            "__groups": [
                {
                    "key": {"value": 0},
                    "__count": 4,
                    "numeric_value:sum": 1.0 + 2.0 + 3.0 + 4.0,
                    "__groups": [
                        {
                            "value": {"value": 0},
                            "__count": 2,
                            "numeric_value:sum": 1.0 + 2.0,
                            "__records": [
                                {"numeric_value": 1.0},
                                {"numeric_value": 2.0},
                            ],
                        },
                        {
                            "value": {"value": 1},
                            "__count": 1,
                            "numeric_value:sum": 1.0 + 2.0,
                            "__records": [
                                {"numeric_value": 3.0},
                            ],
                        },
                    ],
                },
                {
                    "key": {"value": 1},
                    "__count": 3,
                    "numeric_value:sum": 5.0 + 6.0 + 7.0,
                    "__groups": [
                        {
                            "value": {"value": 1},
                            "__count": 2,
                            "numeric_value:sum": 6.0 + 7.0,
                            "__records": [
                                {"numeric_value": 6.0},
                                {"numeric_value": 7.0},
                            ],
                        },
                    ],
                },
                {
                    "key": {"value": 2},
                    "numeric_value:sum": 8.0 + 9.0,
                    "__count": 2,
                },
            ],
            "__count": 3,
        }

        self.assertEqual(res, excepted_result)

        # result = {
        #     'groups': [{
        #         '__domain': [...],
        #         groupby[0]: {'value': groupby[0]_value[, 'label': groupby[0]_value_label]},
        #         aggregates: {
        #             <name_agg>: {'value': groupby[0]_value[, 'label': groupby[0]_value_label]},
        #         },
        #         ...
        #         '__subresult': {
        #             'length':  <length>
        #             'groups': <'groups':....>
        #             OR
        #             'records': [<record_dict>]
        #         }
        #     }]
        #     'length': <length>
        # }
