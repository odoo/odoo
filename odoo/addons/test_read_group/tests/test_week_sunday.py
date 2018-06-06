# -*- coding: utf-8 -*-
from odoo.tests import common


class TestWeekSunday(common.TransactionCase):
    """ Test grouping :week_sunday """
    def setUp(self):
        super(TestWeekSunday, self).setUp()
        self.Model = self.env['test_read_group.on_date']

    def test_week_groupings(self):
        self.Model.create({'date': '2018-06-02', 'value': 1})  # Sat, 22d week
        self.Model.create({'date': '2018-06-03', 'value': 20})  # Sun, 22d or 23d week depending on week start
        self.Model.create({'date': '2018-06-04', 'value': 300})  # Mon, 23d week

        self.assertSequenceEqual.__self__.maxDiff = None


        gb = self.Model.read_group([], ['date', 'value'], ['date:week'], lazy=False)

        self.assertSequenceEqual(sorted(gb, key=lambda r: r['date:week'] or ''), [{
            '__count': 2,
            '__domain': ['&', ('date', '>=', '2018-05-28'), ('date', '<', '2018-06-04')],
            'date:week': 'W22 2018',
            'value': 21,
        }, {
            '__count': 1,
            '__domain': ['&', ('date', '>=', '2018-06-04'), ('date', '<', '2018-06-11')],
            'date:week': 'W23 2018',
            'value': 300,
        }])

        gb = self.Model.read_group([], ['date', 'value'], ['date:week_sunday'], lazy=False)

        self.assertSequenceEqual(sorted(gb, key=lambda r: r['date:week_sunday'] or ''), [{
            '__count': 1,
            '__domain': ['&', ('date', '>=', '2018-05-27'), ('date', '<', '2018-06-03')],
            'date:week_sunday': 'W22(s) 2018',
            'value': 1,
        }, {
            '__count': 2,
            '__domain': ['&', ('date', '>=', '2018-06-03'), ('date', '<', '2018-06-10')],
            'date:week_sunday': 'W23(s) 2018',
            'value': 320,
        }])
