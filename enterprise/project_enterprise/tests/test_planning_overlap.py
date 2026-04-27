# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from markupsafe import Markup

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.fields import Command
from odoo.tests import Form, freeze_time

# Time is freezed on a monday
@freeze_time('2100-01-04')
class TestPlanningOverlap(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = (datetime.now()).replace(hour=0, minute=0, second=0)
        cls.task_1.write({
            'planned_date_begin': cls.today + relativedelta(hour=8),
            'date_deadline': cls.today + relativedelta(hour=10),
            'allocated_hours': 2,
        })

    def test_same_user_no_overlap(self):
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.today + relativedelta(days=+1, hour=8),
            'date_deadline': self.today + relativedelta(days=+1, hour=10),
            'allocated_hours': 3,
        })

        self.assertFalse(self.task_1.planning_overlap)
        self.assertFalse(self.task_2.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_different_users_overlap(self):
        self.task_2.write({
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=11),
            'allocated_hours': 2,
        })

        self.assertFalse(self.task_1.planning_overlap)
        self.assertFalse(self.task_2.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

        (self.task_1 + self.task_2).write({
            'user_ids': [
                Command.link(self.user_projectuser.id),
                Command.link(self.user_projectmanager.id),
            ],
        })

        self.assertEqual(self.task_1.planning_overlap, Markup('<p>Armande ProjectUser has 1 tasks at the same time. Bastien ProjectManager has 1 tasks at the same time.</p>'))
        self.assertEqual(self.task_2.planning_overlap, Markup('<p>Armande ProjectUser has 1 tasks at the same time. Bastien ProjectManager has 1 tasks at the same time.</p>'))

    def test_same_user_overlap(self):
        self.task_2.write({
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=11),
            'allocated_hours': 2,
        })
        (self.task_1 + self.task_2).write({
            'user_ids': self.user_projectuser,
        })

        self.assertEqual(self.task_1.planning_overlap, Markup('<p>Armande ProjectUser has 1 tasks at the same time.</p>'))
        self.assertEqual(self.task_2.planning_overlap, Markup('<p>Armande ProjectUser has 1 tasks at the same time.</p>'))

        search_result = self.env['project.task'].search([('planning_overlap', '=', True)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_overlap_with_allocated_hours_less_than_workable_hours(self):
        self.task_2.write({
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=17),
        })
        self.task_2.allocated_hours = 2

        (self.task_1 + self.task_2).write({
            'user_ids': self.user_projectuser,
        })

        self.assertFalse(self.task_1.planning_overlap, "planning_overlap should be set to False, as the 2 tasks overlap\
                        but the sum of their allocated hours is less than the workable hours of the employee of the period\
                        covered by the tasks.")
        self.assertFalse(self.task_2.planning_overlap, "planning_overlap should be set to False, as the 2 tasks overlap\
                        but the sum of their allocated hours is less than the workable hours of the employee of the period\
                        covered by the tasks.")

        search_result = self.env['project.task'].search([('planning_overlap', '!=', False)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_past_overlap(self):
        tasks = self.task_1 + self.task_2
        with freeze_time('1900-01-04'):
            tasks.with_context(mail_auto_subscribe_no_notify=True).write({
                'user_ids': self.user_projectuser,
                'planned_date_begin': datetime.now() + relativedelta(hours=8),
                'date_deadline': datetime.now() + relativedelta(hours=10),
            })

        self.assertFalse(self.task_1.planning_overlap)
        self.assertFalse(self.task_2.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_done_overlap(self):
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=11),
            'allocated_hours': 2,
            'state': '1_done',
        })

        self.assertFalse(self.task_1.planning_overlap)
        self.assertFalse(self.task_2.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_overlap_for_same_user(self):
        self.task_2.write({
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=11),
            'allocated_hours': 2,
        })
        (self.task_1 + self.task_2).write({
            'user_ids': self.user_projectuser,
        })

        with Form(self.task_2) as task_form:
            task_form.planned_date_begin = False
            task_form.date_deadline = False

        search_result = self.env['project.task'].search([('planning_overlap', '=', True)])
        self.assertFalse(search_result)
