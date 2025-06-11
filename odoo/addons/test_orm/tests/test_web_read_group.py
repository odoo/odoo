from odoo.tests import common


class TestWebReadGroup(common.TransactionCase):
    """ Test the 'length' logic of web_read_group, groups logic
    are tested in test_formatted_read_group """

    maxDiff = None

    def test_limit_offset_performance(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1, 'value': 1})
        Model.create({'key': 1, 'value': 2})
        Model.create({'key': 1, 'value': 3})
        Model.create({'key': 2, 'value': 4})
        Model.create({'key': 2})
        Model.create({'key': 2, 'value': 5})
        Model.create({})
        Model.create({'value': 6})

        # warmup
        Model.web_read_group([], groupby=['key'], aggregates=['value:sum'])

        # One _read_group/query because limit is reached
        with self.assertQueryCount(1):
            self.assertEqual(
                Model.web_read_group([], groupby=['key'], aggregates=['value:sum'], limit=4),
                {
                    'groups': [
                        {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 1 + 2 + 3},
                        {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                        {'__extra_domain': [('key', '=', False)], 'key': False, 'value:sum': 6},
                    ],
                    'length': 3,
                },
            )

        # One _read_group with the limit and other without to get the length
        with self.assertQueryCount(2):
            self.assertEqual(
                Model.web_read_group([], groupby=['key'], aggregates=['value:sum'], limit=2),
                {
                    'groups': [
                        {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 1 + 2 + 3},
                        {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                    ],
                    'length': 3,
                },
            )

        # One _read_group/query because limit is reached
        with self.assertQueryCount(1):
            self.assertEqual(
                Model.web_read_group([], groupby=['key'], aggregates=['value:sum'], offset=1),
                {
                    'groups': [
                        {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                        {'__extra_domain': [('key', '=', False)], 'key': False, 'value:sum': 6},
                    ],
                    'length': 3,
                },
            )

        with self.assertQueryCount(2):
            self.assertEqual(
                Model.web_read_group([], groupby=['key'], aggregates=['value:sum'], offset=1, limit=2, order='key DESC'),
                {
                    'groups': [
                        {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                        {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 1 + 2 + 3},
                    ],
                    'length': 3,
                },
            )
