# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCommon


@tagged('post_install', '-at_install')
class TestActivityScheduleProjectTask(MailCommon):
    """Test activity scheduling with different user access levels.

    Uses project.task as a sample model to verify that:
    - Admin users can schedule activities for anyone without errors
    - Users without write access can schedule activities for themselves
    - Users without write access cannot schedule activities for others
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({'name': 'Test Project'})
        cls.task = cls.env['project.task'].create([
            {'name': 'Task A', 'project_id': cls.project.id},
            {'name': 'Task B', 'project_id': cls.project.id},
            {'name': 'Task C', 'project_id': cls.project.id},
        ])
        cls.plan = cls.env['mail.activity.plan'].create({
            'name': 'Test Plan',
            'res_model': 'project.task',
            'active': True,
        })
        cls.activity_type = cls.env.ref('mail.mail_activity_data_meeting')
        cls.template = cls.env['mail.activity.plan.template'].create({
            'plan_id': cls.plan.id,
            'activity_type_id': cls.activity_type.id,
            'delay_count': 1,
            'delay_unit': 'days',
            'delay_from': 'after_plan_date',
            'sequence': 1,
        })
        cls.readonly_user = cls.env['res.users'].create({
            'name': "Readonly User",
            'login': 'readonly_user',
            'email': 'readonly_user@example.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    def _new_activity_schedule_wizard(self, records):
        """Helper method to create an activity schedule wizard"""
        return self.env['mail.activity.schedule'].with_context(
            active_model=records._name,
            active_ids=records.ids,
        ).new()

    def test_activity_schedule_project_task(self):
        """Test activity scheduling on project tasks with different access levels"""
        task_records = self.task[:3]

        # Admin can schedule activity without any error
        form = self._new_activity_schedule_wizard(task_records).with_user(self.user_admin)
        form.activity_user_id = self.readonly_user
        self.assertFalse(form.has_error)
        self.assertFalse(form.error)

        # User with no write access can schedule activity for themselves
        form = self._new_activity_schedule_wizard(task_records).with_user(self.readonly_user)
        form.activity_user_id = self.readonly_user
        self.assertFalse(form.has_error)

        # User with no write access cannot schedule activity for others
        form.activity_user_id = self.user_admin
        self.assertTrue(form.has_error)
        self.assertIn("You don't have write access on this record to schedule activity for others.", form.error)
