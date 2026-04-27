# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Datetime
from odoo.osv import expression

from odoo.addons.project.models.project_task import CLOSED_STATES
from odoo.addons.project_enterprise.tests.test_task_gantt_view import TestTaskGanttView


class TestTaskGanttViewWithSkills(TestTaskGanttView):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        employee_vals_list = []
        for i, user in enumerate([cls.user_gantt_test_1, cls.user_gantt_test_2, cls.user_gantt_test_3], 1):
            employee_vals_list.append({
                'name': f'Test Employee {i}',
                'user_id': user.id,
            })
        cls.employee_1, cls.employee_2, cls.employee_3 = cls.env['hr.employee'].create(employee_vals_list)
        levels = cls.env['hr.skill.level'].create([{
            'name': f'Level {x}',
            'level_progress': x * 10,
        } for x in range(10)])
        skill_type = cls.env['hr.skill.type'].create({
            'name': 'Languages',
            'skill_level_ids': levels.ids,
        })
        cls.fr_skill, cls.en_skill, cls.es_skill = cls.env['hr.skill'].create([
            {'name': 'French', 'skill_type_id': skill_type.id},
            {'name': 'English', 'skill_type_id': skill_type.id},
            {'name': 'Spanish', 'skill_type_id': skill_type.id},
        ])
        cls.env['hr.employee.skill'].create([
            {
                'employee_id': cls.employee_1.id,
                'skill_id': cls.fr_skill.id,
                'skill_level_id': levels[1].id,
                'skill_type_id': skill_type.id,
            }, {
                'employee_id': cls.employee_1.id,
                'skill_id': cls.en_skill.id,
                'skill_level_id': levels[-1].id,
                'skill_type_id': skill_type.id,
            }, {
                'employee_id': cls.employee_2.id,
                'skill_id': cls.en_skill.id,
                'skill_level_id': levels[-2].id,
                'skill_type_id': skill_type.id,
            }, {
                'employee_id': cls.employee_3.id,
                'skill_id': cls.es_skill.id,
                'skill_level_id': levels[-2].id,
                'skill_type_id': skill_type.id,
            },
        ])

    def test_empty_line_task_last_period(self):
        """ In the gantt view of the tasks of a project, there should be an empty
            line for a user if they have a task planned in the last or current
            period for that project, whether or not is open.
        """
        super().test_empty_line_task_last_period()
        domain = [
            ('project_id', '=', self.project_gantt_test_1.id),
            ('is_closed', '=', False),
        ]

        domain_with_skill = expression.AND([
            domain,
            [('user_skill_ids', 'ilike', self.fr_skill.name)],
        ])
        displayed_gantt_users = self.env['project.task'].with_context({
            'gantt_start_date': Datetime.to_datetime('2023-02-01'),
            'gantt_scale': 'month',
        })._group_expand_user_ids(None, domain_with_skill)

        self.assertTrue(self.user_gantt_test_1 in displayed_gantt_users, 'There should be an empty line for test user 1')
        self.assertFalse(self.user_gantt_test_2 in displayed_gantt_users, 'There should not be an empty line for test user 2')
        self.assertFalse(self.user_gantt_test_3 in displayed_gantt_users, 'There should not be an empty line for test user 3')

        domain_with_skill = expression.AND([
            domain,
            [('user_skill_ids', 'ilike', self.en_skill.name)],
        ])
        displayed_gantt_users = self.env['project.task'].with_context({
            'gantt_start_date': Datetime.to_datetime('2023-02-01'),
            'gantt_scale': 'month',
        })._group_expand_user_ids(None, domain_with_skill)

        self.assertTrue(self.user_gantt_test_1 in displayed_gantt_users, 'There should be an empty line for test user 1')
        self.assertTrue(self.user_gantt_test_2 in displayed_gantt_users, 'There should be an empty line for test user 2')
        self.assertFalse(self.user_gantt_test_3 in displayed_gantt_users, 'There should not be an empty line for test user 3')

        domain_with_skill = expression.AND([
            domain,
            [('user_skill_ids', 'ilike', self.es_skill.name)],
        ])
        displayed_gantt_users = self.env['project.task'].with_context({
            'gantt_start_date': Datetime.to_datetime('2023-02-01'),
            'gantt_scale': 'month',
        })._group_expand_user_ids(None, domain_with_skill)

        self.assertFalse(self.user_gantt_test_1 in displayed_gantt_users, 'There should not be an empty line for test user 1')
        self.assertFalse(self.user_gantt_test_2 in displayed_gantt_users, 'There should not be an empty line for test user 2')
        self.assertTrue(self.user_gantt_test_3 in displayed_gantt_users, 'There should be an empty line for test user 3')

    def test_empty_line_task_last_period_all_tasks(self):
        """ In the gantt view of the 'All Tasks' action, there should be an empty
            line for a user if they have a task planned in the last or current
            period for any project (private tasks are excluded), whether or not
            that task is open.
        """
        super().test_empty_line_task_last_period_all_tasks()
        domain = [('is_closed', '=', False)]
        domain_with_skill = expression.AND([
            domain,
            [('user_skill_ids', 'ilike', self.fr_skill.name)],
        ])
        ProjectTask = self.env['project.task'].with_context({
            'gantt_start_date': Datetime.to_datetime('2023-01-02'),
            'gantt_scale': 'day',
        })
        displayed_gantt_users = ProjectTask._group_expand_user_ids(None, domain_with_skill)

        self.assertTrue(self.user_gantt_test_1 in displayed_gantt_users, 'There should be an empty line for test user 1')
        self.assertFalse(self.user_gantt_test_2 in displayed_gantt_users, 'There should not be an empty line for test user 2')
        self.assertFalse(self.user_gantt_test_3 in displayed_gantt_users, 'There should not be an empty line for test user 3')

        domain_with_skill = expression.AND([
            domain,
            [('user_skill_ids', 'ilike', self.en_skill.name)],
        ])
        displayed_gantt_users = ProjectTask._group_expand_user_ids(None, domain_with_skill)

        self.assertTrue(self.user_gantt_test_1 in displayed_gantt_users, 'There should be an empty line for test user 1')
        self.assertTrue(self.user_gantt_test_2 in displayed_gantt_users, 'There should be an empty line for test user 2')
        self.assertFalse(self.user_gantt_test_3 in displayed_gantt_users, 'There should not be an empty line for test user 3')

        domain_with_skill = expression.AND([
            domain,
            [('user_skill_ids', 'ilike', self.es_skill.name)],
        ])
        displayed_gantt_users = ProjectTask._group_expand_user_ids(None, domain_with_skill)

        self.assertFalse(self.user_gantt_test_1 in displayed_gantt_users, 'There should not be an empty line for test user 1')
        self.assertFalse(self.user_gantt_test_2 in displayed_gantt_users, 'There should not be an empty line for test user 2')
        self.assertTrue(self.user_gantt_test_3 in displayed_gantt_users, 'There should not be an empty line for test user 3')
