# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Datetime
from odoo.tests import new_test_user

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.project.models.project_task import CLOSED_STATES


class TestTaskGanttView(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_gantt_test_1, cls.user_gantt_test_2, cls.user_gantt_test_3 = (
            new_test_user(cls.env, login=f'ganttviewuser{i}', groups='project.group_project_user')
            for i in range(1, 4)
        )
        cls.project_gantt_test_1, cls.project_gantt_test_2 = cls.env['project.project'].create([{
            'name': 'Project Gantt View Test',
        }] * 2)

    def test_empty_line_task_last_period(self):
        """ In the gantt view of the tasks of a project, there should be an empty
            line for a user if they have a task planned in the last or current
            period for that project, whether or not is open.
        """
        self.env['project.task'].with_context({'mail_create_nolog': True}).create([{
            'name': 'Proute',
            'user_ids': user,
            'project_id': self.project_gantt_test_1.id,
            'state': state,
            'planned_date_begin': planned_date,
            'date_deadline': planned_date,
        } for user, state, planned_date in [
            (self.user_gantt_test_1, '1_done', Datetime.to_datetime('2023-01-01')),
            (self.user_gantt_test_2, '01_in_progress', Datetime.to_datetime('2023-01-01')),
            (self.user_gantt_test_3, '1_done', Datetime.to_datetime('2023-02-15')),
        ]])

        domain = [
            ('project_id', '=', self.project_gantt_test_1.id),
            ('state', 'not in', list(CLOSED_STATES)),
        ]

        displayed_gantt_users = self.env['project.task'].with_context({
            'gantt_start_date': Datetime.to_datetime('2023-02-01'),
            'gantt_scale': 'month',
        })._group_expand_user_ids(None, domain, None)

        self.assertTrue(self.user_gantt_test_1 in displayed_gantt_users, 'There should be an empty line for test user 1')
        self.assertTrue(self.user_gantt_test_2 in displayed_gantt_users, 'There should be an empty line for test user 2')
        self.assertTrue(self.user_gantt_test_3 in displayed_gantt_users, 'There should be an empty line for test user 3')

    def test_empty_line_task_last_period_all_tasks(self):
        """ In the gantt view of the 'All Tasks' action, there should be an empty
            line for a user if they have a task planned in the last or current
            period for any project (private tasks are excluded), whether or not
            that task is open.
        """
        self.env['project.task'].with_context({'mail_create_nolog': True}).create([{
            'name': 'Proute',
            'user_ids': user,
            'project_id': project_id,
            'state': '1_done',
            'planned_date_begin': planned_date,
            'date_deadline': planned_date,
        } for project_id, user, planned_date in [
            (self.project_gantt_test_1.id, self.user_gantt_test_1, Datetime.to_datetime('2023-01-01')),
            (self.project_gantt_test_2.id, self.user_gantt_test_2, Datetime.to_datetime('2023-01-02')),
            (False, self.user_gantt_test_3, Datetime.to_datetime('2023-01-01'))
        ]])

        displayed_gantt_users = self.env['project.task'].with_context({
            'gantt_start_date': Datetime.to_datetime('2023-01-02'),
            'gantt_scale': 'day',
        })._group_expand_user_ids(None, [('state', 'not in', list(CLOSED_STATES))], None)

        self.assertTrue(self.user_gantt_test_1 in displayed_gantt_users, 'There should be an empty line for test user 1')
        self.assertTrue(self.user_gantt_test_2 in displayed_gantt_users, 'There should be an empty line for test user 2')
        self.assertFalse(self.user_gantt_test_3 in displayed_gantt_users, 'There should be no empty line for test user 3')
