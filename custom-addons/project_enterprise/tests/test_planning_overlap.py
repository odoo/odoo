# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from markupsafe import Markup

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.fields import Command


class TestPlanningOverlap(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tomorrow = datetime.now() + relativedelta(days=1)
        cls.task_1.write({
            'planned_date_begin': cls.tomorrow + relativedelta(hour=8),
            'date_deadline': cls.tomorrow + relativedelta(hour=10),
        })

    def test_same_user_no_overlap(self):
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.tomorrow + relativedelta(days=+1, hour=8),
            'date_deadline': self.tomorrow + relativedelta(days=+1, hour=10),
        })

        self.assertFalse(self.task_1.planning_overlap)
        self.assertFalse(self.task_2.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_different_users_overlap(self):
        self.task_2.write({
            'planned_date_begin': self.tomorrow + relativedelta(hour=9),
            'date_deadline': self.tomorrow + relativedelta(hour=11),
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
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.tomorrow + relativedelta(hour=9),
            'date_deadline': self.tomorrow + relativedelta(hour=11),
        })

        self.assertEqual(self.task_1.planning_overlap, Markup('<p>Armande ProjectUser has 1 tasks at the same time.</p>'))
        self.assertEqual(self.task_2.planning_overlap, Markup('<p>Armande ProjectUser has 1 tasks at the same time.</p>'))

        search_result = self.env['project.task'].search([('planning_overlap', '=', True)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_past_overlap(self):
        tasks = self.task_1 + self.task_2
        tasks.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.tomorrow + relativedelta(days=-5, hour=9),
            'date_deadline': self.tomorrow + relativedelta(days=-5, hour=11),
        })

        self.assertFalse(self.task_1.planning_overlap)
        self.assertFalse(self.task_2.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)

    def test_same_user_done_overlap(self):
        self.task_2.write({
            'user_ids': self.user_projectuser,
            'planned_date_begin': self.tomorrow + relativedelta(hour=9),
            'date_deadline': self.tomorrow + relativedelta(hour=11),
            'state': '1_done',
        })

        self.assertFalse(self.task_1.planning_overlap)
        self.assertFalse(self.task_2.planning_overlap)

        search_result = self.env['project.task'].search([('planning_overlap', '=', False)])
        self.assertIn(self.task_1, search_result)
        self.assertIn(self.task_2, search_result)
