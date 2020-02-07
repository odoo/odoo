# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import SavepointCase
from unittest.mock import patch


class TestProjectRecurrency(SavepointCase):

    # 1) create a project with allow_recurring_tasks true
    # 2) create a first_task with recurrency true, + parameters
    # 3) mark the task as done
    # 4) run the cron
    # 5) check if the child task has been created task with parent_id = first_task.id 
    # 6) mark the child task as done and check if the recurrency_next_date of the first_task has been set accordingly
    # 7) run the cron 1 day later and repeat step 5 and 6
    # 8) run the cron again, no child task should have been created

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stage1 = cls.env['project.task.type'].create({
            'name': 'New',
            'sequence': 1,
            'is_closed': False
        })

        cls.stage2 = cls.env['project.task.type'].create({
            'name': 'Done',
            'sequence': 2,
            'is_closed': True
        })

        project = cls.env['project.project'].create({
            'name': 'Test',
            'type_ids': [cls.stage1.id, cls.stage2.id],
            'allow_recurring_tasks': True})

        cls.task = cls.env['project.task'].create({
            'name': 'Recurrent Task',
            'project_id': project.id,
        })

    # def test_project_recurrency_count(self):
    #     # recurrency parameters : every week for 2 repetitions. The task is to be created 6 days before it has to be completed
    #     # 4a) check that no task as been created
    #     # 4b) set date_end of task date to yesterday
    #     # 4c) run the cron again

    #     self.task.write({
    #         'recurrency': True,
    #         'recurrency_interval': 1,
    #         'recurrency_type': 'weeks',
    #         'recurrency_end_type': 'count',
    #         'recurrency_count': 2,
    #         'recurrency_before_interval': 6,
    #         'recurrency_before_type': 'days'
    #     })
    #     self.assertFalse(self.task.recurring_next_date)

    #     self.task.write({
    #         'stage_id': self.stage2.id,
    #     })
    #     self.assertEqual(self.task.recurring_next_date, fields.Date.today() + relativedelta(days=7))
    #     self.env['project.task']._cron_create_recurring_tasks()
    #     self.assertFalse(self.env['project.task'].search([('recurring_parent_id', '=', self.task.id)]))

    #     self.task.write({
    #         'date_end': self.task.date_end - relativedelta(days=1)
    #     })

    #     self.env['project.task']._cron_create_recurring_tasks()
    #     child_task = self.env['project.task'].search([('recurring_parent_id', '=', self.task.id)])
    #     self.assertTrue(child_task)
    #     self.assertEqual(child_task.recurring_parent_id, self.task)

    #     # recurring_next_date is False as long as the last task in the chain isn't marked as done
    #     self.assertFalse(self.task.recurring_next_date)

    #     child_task.write({
    #         'stage_id': self.stage2.id,
    #     })

    #     self.assertEqual(self.task.recurring_next_date, fields.Date.today() + relativedelta(days=7))
    #     self.assertEqual(child_task.recurring_next_date, fields.Date.today() + relativedelta(days=7))

    #     child_task.write({
    #         'date_end': child_task.date_end - relativedelta(days=1)
    #     })
    #     self.assertEqual(self.task.recurring_next_date, fields.Date.today() + relativedelta(days=6))
    #     self.env['project.task']._cron_create_recurring_tasks()
    #     self.assertEqual(len(self.env['project.task'].search([('recurring_parent_id', '=', self.task.id)])), 2)

    #     child_task = self.env['project.task'].search([('recurring_parent_id', '=', self.task.id), ('date_end', '=', False)])
    #     self.assertEqual(child_task.recurring_parent_id, self.task)

    #     # recurring_next_date is False as long as the last task in the chain isn't marked as done
    #     self.assertFalse(self.task.recurring_next_date)

    #     child_task.write({
    #         'stage_id': self.stage2.id,
    #     })

    #     # The number of children tasks is 2 so the repetion should stop and no more recurring_next_date is set
    #     self.assertFalse(self.task.recurring_next_date)

    #     # No next date is set so the cron shouldn't create a new task
    #     self.env['project.task']._cron_create_recurring_tasks()
    #     self.assertEqual(len(self.env['project.task'].search([('recurring_parent_id', '=', self.task.id)])), 2)

    # def test_project_recurrency_until(self):
    #     # recurrency parameters : every 2 days until today()+5. The task is to be created 1 days before it has to be completed
    #     # 4a) check that no task as been created
    #     # 4b) set date.today() to tomorrow
    #     # 4c) run the cron again

    #     self.patcher = patch('odoo.addons.project.models.project.fields.Date', wraps=fields.Date)
    #     self.mock_date = self.patcher.start()

    #     self.task.write({
    #         'recurrency': True,
    #         'recurrency_interval': 2,
    #         'recurrency_type': 'days',
    #         'recurrency_end_type': 'last_date',
    #         'recurrency_until_date': fields.Date.today() + relativedelta(days=5),
    #         'recurrency_before_interval': 1,
    #         'recurrency_before_type': 'days'
    #     })
    #     self.assertFalse(self.task.recurring_next_date)

    #     self.task.write({
    #         'stage_id': self.stage2.id,
    #     })
    #     self.assertEqual(self.task.recurring_next_date, fields.Date.today() + relativedelta(days=2))
    #     self.env['project.task']._cron_create_recurring_tasks()
    #     self.assertFalse(self.env['project.task'].search([('recurring_parent_id', '=', self.task.id)]))

    #     # today = set to +1
    #     self.mock_date.today.return_value = fields.Date.today() + relativedelta(days=1)
    #     self.env['project.task']._cron_create_recurring_tasks()
    #     child_task = self.env['project.task'].search([('recurring_parent_id', '=', self.task.id)])
    #     self.assertTrue(child_task)
    #     self.assertEqual(child_task.recurring_parent_id, self.task)

    #     # recurring_next_date is False as long as the last task in the chain isn't marked as done
    #     self.assertFalse(self.task.recurring_next_date)

    #     # today = set to +2
    #     self.mock_date.today.return_value = fields.Date.today() + relativedelta(days=1)
    #     child_task.write({
    #         'stage_id': self.stage2.id,
    #     })
    #     child_task.write({
    #         'date_end': fields.Date.today()
    #     })
    #     self.assertEqual(self.task.recurring_next_date, fields.Date.today() + relativedelta(days=2))
    #     self.assertEqual(child_task.recurring_next_date, fields.Date.today() + relativedelta(days=2))

    #     # today = set to +3
    #     self.mock_date.today.return_value = fields.Date.today() + relativedelta(days=1)
    #     self.env['project.task']._cron_create_recurring_tasks()
    #     self.assertEqual(len(self.env['project.task'].search([('recurring_parent_id', '=', self.task.id)])), 2)

    #     child_task = self.env['project.task'].search([('recurring_parent_id', '=', self.task.id), ('date_end', '=', False)])
    #     self.assertEqual(child_task.recurring_parent_id, self.task)

    #     # recurring_next_date is False as long as the last task in the chain isn't marked as done
    #     self.assertFalse(self.task.recurring_next_date)

    #     # today = set to +4
    #     self.mock_date.today.return_value = fields.Date.today() + relativedelta(days=1)

    #     child_task.write({
    #         'stage_id': self.stage2.id,
    #     })
    #     child_task.write({
    #         'date_end': fields.Date.today()
    #     })

    #     # The number of children tasks is 2 so the repetion should stop and no more recurring_next_date is set
    #     self.assertFalse(self.task.recurring_next_date)

    #     # today = set to +5
    #     self.mock_date.today.return_value = fields.Date.today() + relativedelta(days=1)
    #     # No next date is set so the cron shouldn't create a new task
    #     self.env['project.task']._cron_create_recurring_tasks()
    #     self.assertEqual(len(self.env['project.task'].search([('recurring_parent_id', '=', self.task.id)])), 2)
    #     self.patcher.stop()
