from odoo import fields
from odoo.tests import common, new_test_user
from odoo import Command

class TestPrivateReadGroupingSet(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_user = new_test_user(cls.env, login='Base User', groups='base.group_user')

    def test_simple_read_grouping_set(self):
        Model = self.env['test_read_group.aggregate']
        Partner = self.env['res.partner']
        partner_1 = Partner.create({'name': 'z_one'})
        partner_2 = Partner.create({'name': 'a_two'})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 1})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 2})
        Model.create({'key': 1, 'partner_id': partner_2.id, 'value': 3})
        Model.create({'key': 2, 'partner_id': partner_2.id, 'value': 4})
        Model.create({'key': 2, 'partner_id': partner_2.id})
        Model.create({'key': 2, 'value': 5})
        Model.create({'partner_id': partner_2.id, 'value': 5})
        Model.create({'value': 6})
        Model.create({})

        with self.assertQueries(["""
            SELECT
                GROUPING(
                    "test_read_group_aggregate"."key",
                    "test_read_group_aggregate"."partner_id"
                ),
                "test_read_group_aggregate"."key",
                "test_read_group_aggregate"."partner_id",
                SUM("test_read_group_aggregate"."value")
            FROM
                "test_read_group_aggregate"
            GROUP BY
                GROUPING SETS (
                    ("test_read_group_aggregate"."key", "test_read_group_aggregate"."partner_id"),
                    ("test_read_group_aggregate"."key"),
                    ("test_read_group_aggregate"."partner_id"),
                    ()
                )
            ORDER BY
                "test_read_group_aggregate"."key" ASC,
                "test_read_group_aggregate"."partner_id" ASC
        """]):
            self.assertEqual(
                Model._read_grouping_set([], [['key', 'partner_id'], ['key'], ['partner_id'], []], aggregates=['value:sum']),
                [
                    [
                        (1, partner_1, 1 + 2),
                        (1, partner_2, 3),
                        (2, partner_2, 4),
                        (2, Partner, 5),
                        (False, partner_2, 5),
                        (False, Partner, 6),
                    ],
                    [
                        (1, 1 + 2 + 3),
                        (2, 4 + 5),
                        (False, 5 + 6),
                    ],
                    [
                        (partner_1, 3),
                        (partner_2, 3 + 4 + 5),
                        (Partner, 5 + 6),
                    ],
                    [(26,)],
                ],
            )

        # Forcing order with many2one, traverse use the order of the comodel (res.partner)
        with self.assertQueries(["""

        """]):
            self.assertEqual(
                Model._read_grouping_set([], [['key', 'partner_id'], ['key'], ['partner_id'], []], aggregates=['value:sum'], order="partner_id, key"),
                [
                    [
                        (1, partner_2, 3),
                        (2, partner_2, 4),
                        (False, partner_2, 5),
                        (1, partner_1, 1 + 2),
                        (2, Partner, 5),
                        (False, Partner, 6),
                    ],
                    [
                        (1, 1 + 2 + 3),
                        (2, 4 + 5),
                        (False, 5 + 6),
                    ],
                    [
                        (partner_2, 3 + 4 + 5),
                        (partner_1, 3),
                        (Partner, 5 + 6),
                    ],
                    [(26,)],
                ],
            )

        # # Same than before but with private method, the order doesn't traverse
        # # many2one order, then the order is based on id of partner
        # with self.assertQueries(["""
        #     SELECT "test_read_group_aggregate"."key",
        #            "test_read_group_aggregate"."partner_id",
        #            SUM("test_read_group_aggregate"."value")
        #     FROM "test_read_group_aggregate"
        #     GROUP BY "test_read_group_aggregate"."key",
        #              "test_read_group_aggregate"."partner_id"
        #     ORDER BY "test_read_group_aggregate"."key" ASC,
        #              "test_read_group_aggregate"."partner_id" ASC
        # """]):
        #     self.assertEqual(
        #         Model._read_group([], groupby=['key', 'partner_id'], aggregates=['value:sum']),
        #         [
        #             (1, partner_1, 1 + 2),
        #             (1, partner_2, 3),
        #             (2, partner_2, 4),
        #             (2, self.env['res.partner'], 5),
        #             (False, partner_2, 5),
        #             (False, self.env['res.partner'], 6),
        #         ],
        #     )