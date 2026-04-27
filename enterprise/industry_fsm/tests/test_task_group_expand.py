# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime, timedelta
from odoo.tests import tagged

from .common import TestIndustryFsmCommon

@tagged('-at_install', 'post_install')
class TestTaskGroupExpand(TestIndustryFsmCommon):

    def test_task_user_ids_group_expand(self):
        # Simulate Gantt view like we do in the project version of this test
        gantt_domain = [
            ('planned_date_begin', '>=', datetime.today()),
            ('date_deadline', '<=', datetime.today() + timedelta(days=7)),
        ]
        Task = self.env['project.task'].with_context({
            'gantt_start_date': datetime.today(),
            'fsm_mode': True,
            'gantt_scale': 'week',
        })

        # Create two tasks for two users: one is planned (has planned_date_begin and date_deadline fields) and the other is not
        Task.create([{
            'name': 'planned task',
            'project_id': self.fsm_project.id,
            'partner_id': self.partner.id,
            'planned_date_begin': datetime.today() + timedelta(days=1),
            'date_deadline': datetime.today() + timedelta(days=2),
            'user_ids': [self.george_user.id],
        }, {
            'name': 'non-planned task',
            'project_id': self.fsm_project.id,
            'partner_id': self.partner.id,
            'user_ids': [self.marcel_user.id],
        }])

        groups = Task.read_group(gantt_domain, ['name'], ['user_ids'])
        user_ids_in_group = [group['user_ids'][0] for group in groups if group['user_ids']]

        self.assertIn(self.george_user.id, user_ids_in_group,
                      "A group should exist for the user if they have a planned task whithin the gantt period.")

        self.assertIn(self.marcel_user.id, user_ids_in_group,
                      "A group should exist for the user if they have a task in an open stage whithin the gantt period.")

        self.assertNotIn(self.henri_user.id, user_ids_in_group,
                         "A group should not exist for the user if they don't have a task whithin the gantt period.")
