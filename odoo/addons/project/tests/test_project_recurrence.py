# -*- coding: utf-8 -*-

from odoo import fields
from odoo.tests import users
from odoo.tests.common import Form, TransactionCase

from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time


class TestProjectRecurrence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestProjectRecurrence, cls).setUpClass()

        user_group_employee = cls.env.ref('base.group_user')
        user_group_project_user = cls.env.ref('project.group_project_user')
        user_group_project_recurring_task = cls.env.ref('project.group_project_recurring_tasks')
        Users = cls.env['res.users'].with_context({'no_reset_password': True})

        cls.env.user.groups_id += user_group_project_recurring_task
        cls.user_projectuser = Users.create({
            'name': 'Armande ProjectUser',
            'login': 'armandel',
            'password': 'armandel',
            'email': 'armande.projectuser@example.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_user.id, user_group_project_recurring_task.id])]
        })

        cls.stage_a = cls.env['project.task.type'].create({'name': 'a'})
        cls.stage_b = cls.env['project.task.type'].create({'name': 'b'})
        cls.project_recurring = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Recurring',
            'type_ids': [
                (4, cls.stage_a.id),
                (4, cls.stage_b.id),
            ]
        })

        cls.classPatch(cls.env.cr, 'now', fields.Datetime.now)

        cls.date_01_01 = datetime.combine(datetime.now() + relativedelta(years=-1, month=1, day=1), time(0, 0))

    def test_recurrence_simple(self):
        with freeze_time(self.date_01_01):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.project_id = self.project_recurring
            form.recurring_task = True
            form.repeat_interval = 5
            form.repeat_unit = 'month'
            form.repeat_type = 'forever'
            task = form.save()

            self.assertTrue(bool(task.recurrence_id), 'should create a recurrence')

            task.write(dict(repeat_interval=2))
            self.assertEqual(task.recurrence_id.repeat_interval, 2, 'recurrence should be updated')

            task.recurring_task = False
            self.assertFalse(bool(task.recurrence_id), 'the recurrence should be deleted')

    def test_recurrent_tasks_fields(self):
        self.env['project.tags'].create({
            'name': 'Test Tag',
        })

        with freeze_time(self.date_01_01):
            form = Form(self.env['project.task'])
            form.project_id = self.project_recurring
            form.name = 'name'
            form.description = 'description'
            form.priority = '1'
            form.stage_id = self.stage_b
            form.tag_ids.add(self.env['project.tags'].search([], limit=1))
            form.date_deadline = self.date_01_01 + relativedelta(weeks=1)

            form.recurring_task = True
            form.repeat_interval = 2
            form.repeat_unit = 'month'
            form.repeat_type = 'forever'
            task = form.save()

        with freeze_time(self.date_01_01 + relativedelta(months=1)):
            task.state = '1_done'
        other_task = task.recurrence_id.task_ids - task

        self.assertEqual(
            other_task.date_deadline, task.date_deadline + relativedelta(months=2),
            "Next occurrence should have previous deadline + interval * unit",
        )
        for copied_field in ['project_id', 'name', 'description', 'tag_ids']:
            self.assertEqual(other_task[copied_field], task[copied_field], f"Next occurrence's {copied_field} should have been copied")

        for reset_field in ['priority', 'stage_id', 'state']:
            self.assertNotEqual(other_task[reset_field], task[reset_field], f"Next occurrence's {reset_field} should have been reset")

    def test_recurrence_until(self):
        with freeze_time(self.date_01_01):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.project_id = self.project_recurring
            form.recurring_task = True
            form.repeat_interval = 1
            form.repeat_unit = 'month'
            form.repeat_type = 'until'
            form.repeat_until = self.date_01_01 + relativedelta(months=1, days=1)
            form.date_deadline = self.date_01_01
            task = form.save()

        task.state = '1_done'
        self.assertEqual(len(task.recurrence_id.task_ids), 2, "Since this is before repeat_until, next occurrence should have been created")

        last_recurring_task = task.recurrence_id.task_ids.filtered(lambda t: t != task)
        last_recurring_task.state = '1_done'
        self.assertEqual(len(task.recurrence_id.task_ids), 2, "Since this is after repeat_until, next occurrence shouldn't have been created")

    def test_recurring_settings_change(self):
        self.env['res.config.settings'] \
            .create({'group_project_recurring_tasks': True}) \
            .execute()
        test_task = self.env['project.task'].create({
            'name': "Recurring Task",
            'project_id': self.project_recurring.id,
            'recurring_task': True,
        })
        self.assertTrue(test_task.recurring_task, 'The "Recurring" feature should be enabled from settings.')
        self.env['res.config.settings'] \
            .create({'group_project_recurring_tasks': False}) \
            .execute()
        self.assertFalse(test_task.recurring_task, 'The "Recurring" feature should not be enabled by default.')

    def test_disabling_recurrence(self):
        """
        Disabling the recurrence of one task in a recurrence suite should disable *all*
        recurrences option on the tasks linked to that recurrence
        """
        with freeze_time(self.date_01_01):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.project_id = self.project_recurring
            form.recurring_task = True
            form.repeat_interval = 5
            form.repeat_unit = 'day'
            form.repeat_type = 'forever'
            task = form.save()

        with freeze_time(self.date_01_01 + relativedelta(day=1)):
            task.state = '1_done'
            other_task = self.project_recurring.task_ids - task

        with freeze_time(self.date_01_01 + relativedelta(day=2)):
            other_task.state = '1_done'

        task_c, task_b, task_a = self.env['project.task'].search([('project_id', '=', self.project_recurring.id)])

        task_b.recurring_task = False

        self.assertFalse(any((task_a + task_b + task_c).mapped('recurring_task')),
                         "All tasks in the recurrence should have their recurrence disabled")

    @users('armandel')
    def test_closed_recurring_task(self):
        """
        When an active user closes a recurring task, the next occurrence should be created
        """
        form = Form(self.env['project.task'])
        form.name = 'test recurring task'
        form.project_id = self.project_recurring
        form.recurring_task = True
        form.repeat_interval = 1
        form.repeat_unit = 'day'
        form.repeat_type = 'forever'
        task = form.save()

        self.assertEqual(len(task.recurrence_id.task_ids), 1, "recurrence should have a single task")
        task.state = '1_done'
        self.assertEqual(len(task.recurrence_id.task_ids), 2, "a new occurrence should have been created")
