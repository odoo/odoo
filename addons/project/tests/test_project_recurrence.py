# -*- coding: utf-8 -*-

from odoo import Command, fields
from odoo.tests import Form, TransactionCase, users

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

        cls.env.user.group_ids += user_group_project_recurring_task
        cls.user_projectuser = Users.create({
            'name': 'Armande ProjectUser',
            'login': 'armandel',
            'password': 'armandel',
            'email': 'armande.projectuser@example.com',
            'group_ids': [(6, 0, [user_group_employee.id, user_group_project_user.id, user_group_project_recurring_task.id])]
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
        cls.user = cls.env['res.users'].create({
            'name': 'Recurring Project User',
            'login': 'RPU',
            'email': 'rp.u@example.com',
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
            form.user_ids = self.user

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
        for copied_field in ['project_id', 'name', 'description', 'tag_ids', 'user_ids']:
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

        with freeze_time(self.date_01_01 + relativedelta(days=30)):
            task.state = '1_done'
        self.assertEqual(len(task.recurrence_id.task_ids), 2, "Since this is before repeat_until, next occurrence should have been created")

        last_recurring_task = task.recurrence_id.task_ids.filtered(lambda t: t != task)
        with freeze_time(self.date_01_01 + relativedelta(days=32)):
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

    def test_recurrence_copy_task_dependency(self):
        self.project_recurring.allow_task_dependencies = True
        parent_task = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Recurring Parent Task',
            'project_id': self.project_recurring.id,
            'recurring_task': True,
            'repeat_interval': 2,
            'repeat_unit': 'month',
            'repeat_type': 'forever',
            'child_ids': [
                Command.create({
                    'name': 'Node 1',
                    'project_id': self.project_recurring.id,
                }),
                Command.create({
                    'name': 'SuperNode 2',
                    'project_id': self.project_recurring.id,
                    'child_ids': [
                        Command.create({
                            'name': 'Node 2',
                            'project_id': self.project_recurring.id,
                        })
                    ],
                }),
                Command.create({
                    'name': 'Node 3',
                    'project_id': self.project_recurring.id,
                }),
            ],
        })

        side_task1, side_task2 = self.env['project.task'].with_context({'mail_create_nolog': True}).create([{
            'name': f"Side Task {i + 1}",
            'project_id': self.project_recurring.id,
        } for i in range(2)])

        node1 = parent_task.child_ids[0]
        node2 = parent_task.child_ids[1].child_ids
        node3 = parent_task.child_ids[2]

        # Dependencies
        node1.dependent_ids = node2
        node2.dependent_ids = node3
        side_task1.dependent_ids = node2
        node3.dependent_ids = side_task2

        # Task recurrence trigger
        parent_task.state = '1_done'
        parent_task_copy = self.env['project.task'].browse(parent_task.recurrence_id._get_last_task_id_per_recurrence_id().get(parent_task.recurrence_id.id))
        self.assertNotEqual(parent_task.id, parent_task_copy.id, 'The generated recurring task should be different than the original one')

        # Newly created nodes from recurrence
        parent_copy_node1 = parent_task_copy.child_ids[0]
        parent_copy_node2 = parent_task_copy.child_ids[1].child_ids
        parent_copy_node3 = parent_task_copy.child_ids[2]

        # The nodes and dependencies ids of the orginal and newly created nodes should be different
        self.assertNotEqual(node1.id, parent_copy_node1.id, 'The original and copied node1 should be different')
        self.assertNotEqual(node2.id, parent_copy_node2.id, 'The original and copied node2 should be different')
        self.assertNotEqual(node3.id, parent_copy_node3.id, 'The original and copied node3 should be different')

        self.assertNotEqual(node1.dependent_ids.ids, parent_copy_node1.dependent_ids.ids, 'The dependencies of the original and copied node1 should be different')
        self.assertEqual(node1.depend_on_ids.ids, parent_copy_node1.depend_on_ids.ids, 'The dependencies of the original and copied node1 should be different')
        self.assertNotEqual(node2.dependent_ids.ids, parent_copy_node2.dependent_ids.ids, 'The dependencies of the original and copied node2 should be different')
        self.assertNotEqual(node2.depend_on_ids.ids, parent_copy_node2.depend_on_ids.ids, 'The dependencies of the original and copied node2 should be different')
        self.assertEqual(node3.dependent_ids.ids, parent_copy_node3.dependent_ids.ids, 'The dependencies of the original and copied node3 should be different')
        self.assertNotEqual(node3.depend_on_ids.ids, parent_copy_node3.depend_on_ids.ids, 'The dependencies of the original and copied node3 should be different')

        # However, the dependency structure of the orginal and newly created nodes should be the same
        self.assertEqual(parent_copy_node1.dependent_ids.ids, parent_copy_node2.ids, 'Node1copy - Node2copy relation should be present')
        self.assertEqual(parent_copy_node2.dependent_ids.ids, parent_copy_node3.ids, 'Node2copy - Node3copy relation should be present')
        self.assertEqual(parent_copy_node3.dependent_ids.ids, side_task2.ids, 'Node3 - SideTask2 relation should be present')

        self.assertEqual(len(parent_copy_node1.depend_on_ids), 0)
        self.assertCountEqual(parent_copy_node2.depend_on_ids.ids, [parent_copy_node1.id, side_task1.id], 'Node2copy - Node1copy and Node2copy - SideTask1 relations should be present')
        self.assertEqual(parent_copy_node3.depend_on_ids.ids, parent_copy_node2.ids, 'Node3copy - Node2copy relation should be present')

        # The original nodes dependencies should remain untouched by the creation of the new nodes
        self.assertEqual(node1.dependent_ids.ids, node2.ids, 'Node1 - Node2 relation should be present')
        self.assertEqual(node2.dependent_ids.ids, node3.ids, 'Node2 - Node3 relation should be present')
        self.assertEqual(node3.dependent_ids.ids, side_task2.ids, 'Node3 - SideTask2 relation should be present')

        self.assertEqual(len(node1.depend_on_ids), 0)
        self.assertCountEqual(node2.depend_on_ids.ids, [node1.id, side_task1.id], 'Node2 - Node1 and Node2 - SideTask1 relations should be present')
        self.assertEqual(node3.depend_on_ids.ids, node2.ids, 'Node3 - Node2 relation should be present')

        # The side tasks should now have dependencies from both the original and copied tasks
        self.assertCountEqual(side_task1.dependent_ids.ids, [node2.id, parent_copy_node2.id], 'SideTask1 - Node2 and SideTask1 - Node2copy relations should be present')
        self.assertEqual(len(side_task2.dependent_ids), 0)

        self.assertEqual(len(side_task1.depend_on_ids), 0)
        self.assertCountEqual(side_task2.depend_on_ids.ids, [node3.id, parent_copy_node3.id], 'SideTask2 - Node3 and SideTask2 - Node3copy relations should be present')

    def test_next_occurrence_batch_call(self):
        tasks = self.env['project.task'].with_context({'mail_create_nolog': True}).create([
            {
                'name': 'Recurring Task 1',
                'project_id': self.project_recurring.id,
                'recurring_task': True,
                'repeat_unit': 'week',
                'repeat_type': 'forever',
                'date_deadline': "2023-01-01 00:00:00",
                'child_ids': [
                    Command.create({
                        'name': 'R1 Sub Task 1',
                        'project_id': self.project_recurring.id,
                        'date_deadline': "2023-01-02 00:00:00",
                        'child_ids': [
                            Command.create({
                                'name': 'R1 Sub Task 2',
                                'project_id': self.project_recurring.id,
                                'date_deadline': "2023-01-03 00:00:00",
                            })
                        ],
                    }),
                ],
            },
            {
                'name': 'Recurring Task 2',
                'project_id': self.project_recurring.id,
                'recurring_task': True,
                'repeat_unit': 'week',
                'repeat_type': 'forever',
                'date_deadline': "2023-01-04 00:00:00",
                'child_ids': [
                    Command.create({
                        'name': 'R2 Sub Task',
                        'project_id': self.project_recurring.id,
                        'date_deadline': "2023-01-05 00:00:00",
                    }),
                ],
            },
        ])
        tasks_copy = self.env['project.task.recurrence']._create_next_occurrences(tasks)
        # Every date should be 1 week later
        self.assertEqual(datetime(2023, 1, 8, 0, 0), tasks_copy[0].date_deadline)
        self.assertEqual(datetime(2023, 1, 9, 0, 0), tasks_copy[0].child_ids.date_deadline)
        self.assertEqual(datetime(2023, 1, 10, 0, 0), tasks_copy[0].child_ids.child_ids.date_deadline)
        self.assertEqual(datetime(2023, 1, 11, 0, 0), tasks_copy[1].date_deadline)
        self.assertEqual(datetime(2023, 1, 12, 0, 0), tasks_copy[1].child_ids.date_deadline)

    def test_recurrent_tasks_without_archive_user(self):
        task = self.env['project.task'].create({
            'project_id': self.project_recurring.id,
            'name': 'Test task',
            'stage_id': self.stage_b.id,
            'user_ids': [Command.set([self.user.id, self.user_projectuser.id])],
            'recurring_task': True,
            'repeat_type': 'forever',
        })
        self.user_projectuser.action_archive()
        task.write({'state': '1_done'})
        self.assertEqual((task.recurrence_id.task_ids - task).user_ids, self.user)

    def test_recurrent_sub_tasks_without_archive_user(self):
        """
        Test the behavior of recurring tasks when a user assigned to a child task is archived.
        Steps:
        1. Create a parent task with a recurring rule.
        2. Add a child task with assigned users.
        3. Archive one of the users assigned to the child task.
        4. Complete the parent task to generate a recurring task.
        5. Verify the new task excludes archived users.
        """
        parent_task = self.env['project.task'].create({
            'project_id': self.project_recurring.id,
            'name': 'Task A',
            'stage_id': self.stage_b.id,
            'recurring_task': True,
            'repeat_type': 'forever',
            'child_ids': [Command.create({
                'project_id': self.project_recurring.id,
                'name': 'Sub task A',
                'stage_id': self.stage_b.id,
                'user_ids': [Command.set([self.user.id, self.user_projectuser.id])],
            })],
        })
        self.user_projectuser.action_archive()
        parent_task.write({'state': '1_done'})
        self.assertEqual((parent_task.recurrence_id.task_ids - parent_task).child_ids.user_ids, self.user)

    def test_close_recurring_task_private_project(self):
        """
            Test that an assigned employee to a recurrent task can close it
            even when they don't have access to the project.

            Test Case:
            ==========
            1) Create a private project with a parent task and a recurrent subtask.
            2) assign an employee to the subtask.
            3) Ensure the employee can close the subtask even if they don't have
               access to the project.
        """
        employee = self.env['res.users'].create({
            'name': 'Employee',
            'login': 'employee',
            'email': 'employee@odoo.com',
            'group_ids': [(6, 0, [self.env.ref('project.group_project_user').id])],
        })
        private_project = self.env['project.project'].create({
            'name': 'Private Project',
            'privacy_visibility': 'followers',
        })
        task = self.env['project.task'].create({
            'name': 'Parent Task',
            'project_id': private_project.id,
            'user_ids': [(4, employee.id)],
            'recurring_task': True,
            'repeat_type': 'forever',
            'state': '01_in_progress',
        })

        self.env.invalidate_all()
        task.with_user(employee).write({'state': '1_done'})
        self.assertEqual(task.state, '1_done', "The employee should be able to mark the task as done.")
