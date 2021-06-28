# -*- coding: utf-8 -*-

from odoo.tests import common


class TestReadProgressBar(common.TransactionCase):
    """Test for read_progress_bar"""

    def setUp(self):
        super(TestReadProgressBar, self).setUp()
        self.Model = self.env['res.partner']

    def test_week_grouping(self):
        """The labels associated to each record in read_progress_bar should match
        the ones from read_group, even in edge cases like en_US locale on sundays
        """
        context = {"lang": "en_US"}
        groupby = "date:week"
        self.Model.create({'date': '2021-05-02', 'name': "testWeekGrouping_first"}) # Sunday
        self.Model.create({'date': '2021-05-09', 'name': "testWeekGrouping_second"}) # Sunday
        progress_bar = {
            'field': 'name',
            'colors': {
                "testWeekGrouping_first": 'success',
                "testWeekGrouping_second": 'danger',
            }
        }
        
        groups = self.Model.with_context(context).read_group(
            [('name', "like", "testWeekGrouping%")], fields=['date', 'name'], groupby=[groupby])
        progressbars = self.Model.with_context(context).read_progress_bar(
            [('name', "like", "testWeekGrouping%")], group_by=groupby, progress_bar=progress_bar)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(progressbars), 2)

        # format the read_progress_bar result to get a dictionary under this format : {record_name: group_name}
        # original format (after read_progress_bar) is : {group_name: {record_name: count}}
        pg_groups = {
            next(record_name for record_name, count in data.items() if count): group_name \
                for group_name, data in progressbars.items()
        }

        self.assertEqual(groups[0][groupby], pg_groups["testWeekGrouping_first"])
        self.assertEqual(groups[1][groupby], pg_groups["testWeekGrouping_second"])
