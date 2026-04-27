# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tests import Form, tagged
from freezegun import freeze_time

from odoo import Command
from .common import TestIndustryFsmCommon

@tagged('post_install', '-at_install')
class TestFsmProjectTask(TestIndustryFsmCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = cls.env['res.users'].create({
            'name': 'blue',
            'login': 'blue',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])]
        })

        cls.partner_portal = cls.env['res.partner'].create({
            'name': 'blue partner',
            'company_id': False,
            'user_ids': [Command.link(cls.user_portal.id)]
        })

        cls.project_portal, cls.fsm_project_portal = (cls.env['project.project'].with_context(
            {'mail_create_nolog': True}).create([{
            'name': 'Portal',
            'privacy_visibility': 'portal',
        }, {
            'name': 'FSM Portal',
            'privacy_visibility': 'portal',
            'is_fsm': True,
            'allow_timesheets': True,
            'company_id': cls.env.company.id,
        }]))
        cls.project_portal.message_subscribe(partner_ids=[cls.partner_portal.id])
        cls.fsm_project_portal.message_subscribe(partner_ids=[cls.partner_portal.id])

    def test_default_project_fsm_subtasks(self):
        _, fsm_project_B = self.env['project.project'].create([
            {
                'name': 'Field Service A',
                'is_fsm': True,
                'company_id': self.env.company.id,
                'allow_timesheets': True,
                'sequence': 100,
            },
            {
                'name': 'Field Service B',
                'is_fsm': True,
                'company_id': self.env.company.id,
                'allow_timesheets': True,
                'sequence': 200,
            }
        ])
        task = self.env['project.task'].create({
            'name': 'Fsm task',
            'project_id': fsm_project_B.id,
            'partner_id': self.partner.id,
        })
        subtask = self.env['project.task'].with_context(
                fsm_mode=True,
                default_parent_id=task.id,
                default_project_id=task.project_id.id
        ).create({
            'name': 'Fsm subtask',
            'partner_id': self.partner.id,
        })
        self.assertEqual(subtask.project_id, fsm_project_B)

    @freeze_time("2025-05-12")
    def test_task_fsm_without_calendar(self):
        fsm_project = self.env['project.project'].create({
            'name': 'Field Service A',
            'is_fsm': True,
            'company_id': self.env.company.id,
        })
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee', 'user_id': self.env.user.id,
        })
        employee.resource_id.write({'calendar_id': False})
        now = datetime.combine(datetime.now(), datetime.min.time())

        # first save
        task_form = Form(self.env['project.task'], view="project.view_task_form2")
        task_form.name = 'test task'
        task_form.project_id = fsm_project
        task_form.partner_id = self.partner
        task_form.user_ids = self.env.user
        task_form.planned_date_begin = False
        task_form.date_deadline = False
        task_form.save()

        # second save
        task_form.planned_date_begin = now
        task_form.date_deadline = now + relativedelta(days=1)
        task = task_form.save()
        self.assertEqual(task.allocated_hours, 8.0, "the task allocated hours should be 8.0")

    def test_default_user_is_set_on_fsm_task(self):
        """
        This test ensures that when a fsm task is created, the partner_id set on the current user is set as its default
        partner_id if the user is a portal user.
        """
        (self.project_portal | self.fsm_project_portal).write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })

        portal_task = self.env['project.task'].with_context(
            {'default_project_id': self.project_portal.id}).with_user(self.user_portal).create({'name': 'youpi'})
        fsm_portal_task = self.env['project.task'].with_context(
            {'default_project_id': self.fsm_project_portal.id}).with_user(self.user_portal).create({'name': 'fsm task'})

        self.assertEqual(fsm_portal_task.partner_id, self.partner_portal,
                         'The fsm task created by a portal user should have a default partner set.')
        self.assertFalse(portal_task.partner_id,
                         'The task created by a portal user should not have a default partner set.')

        portal_task, fsm_portal_task = self.env['project.task'].create([{
            'name': 'youpi',
            'project_id': self.project_portal.id,
        }, {
            'name': 'fsm task',
            'project_id': self.fsm_project_portal.id,
        }])
        self.assertFalse(fsm_portal_task.partner_id,
                         'The fsm task created by a standard user should not have a default partner set.')
        self.assertFalse(portal_task.partner_id,
                         'The task created by a standard user should not have a default partner set.')

    def test_fsm_user_task_creation_without_access_error_updates_partner_mobile(self):
        """
        Verify that creating a task with a customer as FSM user
        raises AccessError due to restricted res.partner rights.
        """
        self.assertFalse(self.fsm_user.partner_id.mobile)
        test_task = self.env['project.task'].with_user(self.fsm_user).create({
            'name': 'Test task',
            'project_id': self.fsm_project.id,
            'partner_id': self.fsm_user.partner_id.id,
            'partner_phone': '1234'
        })

        self.assertTrue(test_task.partner_id, "Customer should be set when creating a task with a partner.")
        self.assertEqual(self.fsm_user.partner_id.mobile, '1234', "Partner mobile number should be updated according to the partner_phone field.")
