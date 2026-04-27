# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta

from markupsafe import Markup
from odoo.tests import freeze_time
from .common import TestIndustryFsmCommon

# Time is freezed on a monday
@freeze_time('2100-01-04')
class TestFsmPlanningOverlap(TestIndustryFsmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = datetime.combine(date.today(), time.min)
        cls.task.write({
            'user_ids': cls.george_user,
            'planned_date_begin': cls.today + relativedelta(hour=8),
            'date_deadline': cls.today + relativedelta(hour=10),
            'allocated_hours': 2,
        })

    def test_same_user_no_overlap(self):
        self.second_task.write({
            'user_ids': self.george_user,
            'planned_date_begin': self.today + relativedelta(days=1, hour=8),
            'date_deadline': self.today + relativedelta(days=1, hour=10),
            'allocated_hours': 3,
        })

        self.assertFalse(self.task.planning_overlap)
        self.assertFalse(self.second_task.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task, search_result)
        self.assertIn(self.second_task, search_result)

    def test_different_users_overlap(self):
        self.second_task.write({
            'user_ids': self.marcel_user,
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=11),
            'allocated_hours': 2,
        })

        self.assertFalse(self.task.planning_overlap)
        self.assertFalse(self.second_task.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task, search_result)
        self.assertIn(self.second_task, search_result)

        third_task = self.env['project.task'].create({
            'name': 'Fsm task 3',
            'project_id': self.fsm_project.id,
            'partner_id': self.partner.id,
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=11),
        })

        tasks = self.task + self.second_task + third_task
        tasks.user_ids = self.george_user + self.marcel_user
        for task in tasks:
            self.assertEqual(
                task.planning_overlap,
                Markup('<p>George has 2 tasks at the same time. Marcel has 2 tasks at the same time.</p>'),
            )

    def test_same_user_overlap(self):
        self.second_task.write({
            'user_ids': self.george_user,
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=11),
            'allocated_hours': 2,
        })

        self.assertEqual(self.task.planning_overlap, Markup('<p>George has 1 tasks at the same time.</p>'))
        self.assertEqual(self.second_task.planning_overlap, Markup('<p>George has 1 tasks at the same time.</p>'))

        search_result = self.env['project.task'].search([('planning_overlap', '=', True)])
        self.assertIn(self.task, search_result)
        self.assertIn(self.second_task, search_result)

    def test_same_user_overlap_with_allocated_hours_less_than_workable_hours(self):
        project = self.env['project.project'].create({'name': 'Project'})
        normal_task = self.env['project.task'].create({
            'name': 'Normal Task',
            'project_id': project.id,
            'user_ids': self.george_user,
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=17),
            'allocated_hours': 2,
        })
        self.assertFalse(self.task.planning_overlap, "planning_overlap should be set to False, as the 2 tasks (one FSM and one normal) overlap\
                        but the sum of their allocated hours is less than the workable hours of the employee of the period\
                        covered by the tasks.")
        self.assertFalse(normal_task.planning_overlap, "planning_overlap should be set to False, as the 2 tasks (one FSM and one normal) overlap\
                        but the sum of their allocated hours is less than the workable hours of the employee of the period\
                        covered by the tasks.")

        search_result = self.env['project.task'].search([('planning_overlap', '!=', False)])
        self.assertIn(self.task, search_result)
        self.assertIn(normal_task, search_result)

    def test_same_user_past_overlap(self):
        tasks = self.task + self.second_task
        with freeze_time('1900-01-04'):
            tasks.with_context(mail_auto_subscribe_no_notify=True).write({
                'user_ids': self.george_user,
                'planned_date_begin': datetime.now() + relativedelta(hours=8),
                'date_deadline': datetime.now() + relativedelta(hours=10),
            })

        self.assertFalse(self.task.planning_overlap)
        self.assertFalse(self.second_task.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task, search_result)
        self.assertIn(self.second_task, search_result)

    def test_same_user_done_overlap(self):
        self.second_task.write({
            'user_ids': self.george_user,
            'planned_date_begin': self.today + relativedelta(hour=9),
            'date_deadline': self.today + relativedelta(hour=11),
            'allocated_hours': 2,
            'state': '1_done',
        })

        self.assertFalse(self.task.planning_overlap)
        self.assertFalse(self.second_task.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task, search_result)
        self.assertIn(self.second_task, search_result)
