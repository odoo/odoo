from freezegun import freeze_time

from odoo import exceptions
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.tests import tagged, HttpCase


@tagged("mail_activity")
class TestMailActivityChatter(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_partner = cls.env['res.partner'].create({
            'email': 'test.partner@example.com',
            'name': 'Test User',
        })

    def test_mail_activity_date_format(self):
        with freeze_time("2024-01-01 09:00:00 AM"):
            LANG_CODE = "en_US"
            self.env = self.env(context={"lang": LANG_CODE})
            lang = self.env["res.lang"].search([('code', '=', LANG_CODE)])
            lang.date_format = "%d/%b/%y"
            lang.time_format = "%I:%M:%S %p"

            self.start_tour(
                f"/web#id={self.test_partner.id}&model=res.partner",
                "mail_activity_date_format",
                login="admin",
            )

    def test_mail_activity_schedule_from_chatter(self):
        self.start_tour(
            f"/odoo/res.partner/{self.test_partner.id}",
            "mail_activity_schedule_from_chatter",
            login="admin",
        )


@tagged("mail_activity")
class TestMailActivityIntegrity(ActivityScheduleCase):

    def test_mail_activity_type_master_data(self):
        """ Test master data integrity

          * 'call', 'meeting', 'todo', 'upload document' and 'warning' should always be cross model;
          * 'call', 'meeting' and 'todo' cannot be removed
        """
        call = self.env.ref('mail.mail_activity_data_call')
        meeting = self.env.ref('mail.mail_activity_data_meeting')
        todo = self.env.ref('mail.mail_activity_data_todo')
        upload = self.env.ref('mail.mail_activity_data_upload_document')
        warning = self.env.ref('mail.mail_activity_data_warning')
        with self.assertRaises(exceptions.UserError):
            call.write({'res_model': 'res.partner'})
        with self.assertRaises(exceptions.UserError):
            meeting.write({'res_model': 'res.partner'})
        with self.assertRaises(exceptions.UserError):
            todo.write({'res_model': 'res.partner'})
        with self.assertRaises(exceptions.UserError):
            upload.write({'res_model': 'res.partner'})
        with self.assertRaises(exceptions.UserError):
            warning.write({'res_model': 'res.partner'})

        with self.assertRaises(exceptions.UserError):
            call.unlink()
        with self.assertRaises(exceptions.UserError):
            meeting.unlink()
        with self.assertRaises(exceptions.UserError):
            todo.unlink()

    def test_user_archive_activity_reassignment(self):
        """ Test Archiving a user reassigns to the correct users. """
        user_to_archive = self.user_employee
        inactive_creator = mail_new_test_user(
            self.env, login='archived_employee', name='Archived Employee',
            company_id=self.company_admin.id, groups='base.group_user,base.group_partner_manager',
        )
        base_vals = {
            'activity_type_id': self.activity_type_todo.id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': self.test_partner.id,
            'user_id': user_to_archive.id,
        }

        # (Scenario Name, Creator, Extra Create Vals, Expected User, Expected Role)
        scenarios = [
            ('personal', user_to_archive, {'res_model_id': False, 'res_id': False}, False, False),
            ('active_creator', self.user_admin, {}, self.user_admin, self.env['res.role']),
            ('role_fallback', self.user_admin, {'role_id': self.test_role_1.id}, self.env['res.users'], self.test_role_1),
            ('inactive_creator', inactive_creator, {}, self.env['res.users'], self.env['res.role']),
            ('self_created', user_to_archive, {}, self.env['res.users'], self.env['res.role']),
        ]

        activities = {}
        for name, creator, extra_vals, _, _ in scenarios:
            activities[name] = self.env['mail.activity'].with_user(creator).create({**base_vals, **extra_vals})

        inactive_creator.action_archive()
        user_to_archive.action_archive()

        for name, _, _, exp_user, exp_role in scenarios:
            with self.subTest(scenario=name):
                activity = activities[name]
                if name == 'personal':
                    self.assertFalse(activity.exists(), "Personal activities of archived users should be deleted.")
                else:
                    self.assertTrue(activity.exists())
                    self.assertEqual(activity.user_id, exp_user)
                    self.assertEqual(activity.role_id, exp_role)

    def test_role_archive_and_unlink_constraints(self):
        """ Test that archiving a role keeps its activities. Unlinking is blocked if referenced. """
        role_activity, role_act_type, role_plan, role_action, role_free = self.env['res.role'].create([
            {'name': 'Activity Role'},
            {'name': 'Act Type Role'},
            {'name': 'Plan Role'},
            {'name': 'Action Role'},
            {'name': 'Free Role'},
        ])

        activity = self.env['mail.activity'].with_user(self.user_admin).create({
            'activity_type_id': self.activity_type_todo.id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': self.test_partner.id,
            'role_id': role_activity.id,
            'user_id': False,
        })
        self.env['mail.activity.type'].create({
            'name': 'Test Type', 'default_role_id': role_act_type.id,
        })
        plan = self.env['mail.activity.plan'].create({
            'name': 'Test Plan', 'res_model': 'res.partner',
        })
        self.env['mail.activity.plan.template'].create({
            'summary': 'Test Plan Activity',
            'plan_id': plan.id,
            'activity_type_id': self.activity_type_todo.id,
            'responsible_type': 'role',
            'role_id': role_plan.id,
        })
        self.env['ir.actions.server'].create({
            'name': 'Test Action',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'state': 'next_activity',
            'activity_user_type': 'role',
            'activity_role_id': role_action.id,
        })

        # Test Archiving
        role_activity.action_archive()
        self.assertFalse(role_activity.active)
        self.assertEqual(activity.role_id, role_activity, "Archived role should remain linked to the activity.")

        # Test Unlink
        constraints = [
            (role_activity, '1 unassigned activity'),
            (role_act_type, 'Activity Types: Test Type'),
            (role_plan, 'Activity Plans: Test Plan Activity'),
            (role_action, '1 Server Action'),
        ]
        for role, error_regex in constraints:
            with self.subTest(role=role.name):
                with self.assertRaisesRegex(exceptions.UserError, error_regex):
                    role.unlink()

        role_free.unlink()
        self.assertFalse(self.env['res.role'].browse(role_free.id).exists())
