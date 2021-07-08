# -*- coding: utf-8 -*-
from odoo.tests import common
from odoo import fields
from datetime import timedelta


class TestReadProgressBar(common.TransactionCase):
    """Test for read_progress_bar"""

    def setUp(self):
        super(TestReadProgressBar, self).setUp()
        self.Model = self.env['mail.test.activity']

    def test_week_grouping(self):
        """The labels associated to each record in read_progress_bar should match
        the ones from read_group, even in edge cases like en_US locale on sundays
        """
        context = {"lang": "en_US"}
        model = self.Model.with_context(context)
        groupby = "date:week"
        sunday1 = '2021-05-02'
        sunday2 = '2021-05-09'
        sunday3 = '2021-05-16'
        # Don't mistake fields date and date_deadline:
        # * date is just a random value
        # * date_deadline defines activity_state
        self.Model.create({'date': sunday1, 'name': "Yesterday, all my troubles seemed so far away"}).activity_schedule(
            'test_mail.mail_act_test_todo',
            summary="Make another test super asap (yesterday)",
            date_deadline=fields.Date.context_today(model) - timedelta(days=7)
        )
        self.Model.create({'date': sunday2, 'name': "Things we said today"}).activity_schedule(
            'test_mail.mail_act_test_todo',
            summary="Make another test asap",
            date_deadline=fields.Date.context_today(model)
        )
        self.Model.create({'date': sunday3, 'name': "Tomorrow Never Knows"}).activity_schedule(
            'test_mail.mail_act_test_todo',
            summary="Make a test tomorrow",
            date_deadline=fields.Date.context_today(model) + timedelta(days=7)
        )

        progress_bar = {
            'field': 'activity_state',
            'colors': {
                "overdue": 'danger',
                "today": 'warning',
                "planned": 'success',
            }
        }

        domain = [('date', "!=", False)]
        # call read_group to compute group names
        groups = model.read_group(domain, fields=['date'], groupby=[groupby])
        progressbars = model.read_progress_bar(domain, group_by=groupby, progress_bar=progress_bar)
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(progressbars), 3)

        # format the read_progress_bar result to get a dictionary under this format : {activity_state: group_name}
        # original format (after read_progress_bar) is : {group_name: {activity_state: count}}
        pg_groups = {
            next(activity_state for activity_state, count in data.items() if count): group_name \
                for group_name, data in progressbars.items()
        }

        self.assertEqual(groups[0][groupby], pg_groups["overdue"])
        self.assertEqual(groups[1][groupby], pg_groups["today"])
        self.assertEqual(groups[2][groupby], pg_groups["planned"])
