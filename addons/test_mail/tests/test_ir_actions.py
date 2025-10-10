# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import Command
from odoo.addons.base.tests.test_ir_actions import TestServerActionsBase
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import Form, tagged
from odoo.tools import mute_logger


@tagged('ir_actions')
class TestServerActionsEmail(MailCommon, TestServerActionsBase):

    def setUp(self):
        super(TestServerActionsEmail, self).setUp()
        self.template = self._create_template(
            'res.partner',
            {'email_from': '{{ object.user_id.email_formatted or object.company_id.email_formatted or user.email_formatted }}',
             'partner_to': '%s' % self.test_partner.id,
            }
        )

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_action_email(self):
        # initial state
        self.assertEqual(len(self.test_partner.message_ids), 1,
                         'Contains Contact created message')
        self.assertFalse(self.test_partner.message_partner_ids)

        # update action: send an email
        self.action.write({
            'mail_post_method': 'email',
            'state': 'mail_post',
            'template_id': self.template.id,
        })
        self.assertFalse(self.action.mail_post_autofollow, 'Email action does not support autofollow')

        with self.mock_mail_app():
            self.action.with_context(self.context).run()

        # check an email is waiting for sending
        mail = self.env['mail.mail'].sudo().search([('subject', '=', 'About TestingPartner')])
        self.assertEqual(len(mail), 1)
        self.assertTrue(mail.auto_delete)
        self.assertEqual(mail.body_html, '<p>Hello TestingPartner</p>')
        self.assertFalse(mail.is_notification)
        with self.mock_mail_gateway(mail_unlink_sent=True):
            mail.send()

        # no archive (message)
        self.assertEqual(len(self.test_partner.message_ids), 1,
                         'Contains Contact created message')
        self.assertFalse(self.test_partner.message_partner_ids)

    def test_action_followers(self):
        self.test_partner.message_unsubscribe(self.test_partner.message_partner_ids.ids)
        random_partner = self.env['res.partner'].create({'name': 'Thierry Wololo'})
        self.action.write({
            'state': 'followers',
            'partner_ids': [(4, self.env.ref('base.partner_admin').id), (4, random_partner.id)],
        })
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.message_partner_ids, self.env.ref('base.partner_admin') | random_partner)

    def test_action_followers_warning(self):
        self.test_partner.message_unsubscribe(self.test_partner.message_partner_ids.ids)
        self.action.write({
            'state': 'followers',
            "followers_type": "generic",
            "followers_partner_field_name": "user_id.name"
        })
        self.assertEqual(self.action.warning, "The field 'Salesperson > Name' is not a partner field.")
        self.action.write({"followers_partner_field_name": "parent_id.child_ids"})
        self.assertEqual(self.action.warning, False)

    def test_action_message_post(self):
        # initial state
        self.assertEqual(len(self.test_partner.message_ids), 1,
                         'Contains Contact created message')
        self.assertFalse(self.test_partner.message_partner_ids)

        # test without autofollow and comment
        self.action.write({
            'mail_post_autofollow': False,
            'mail_post_method': 'comment',
            'state': 'mail_post',
            'template_id': self.template.id
        })

        with self.assertSinglePostNotifications(
                [{'partner': self.test_partner, 'type': 'email', 'status': 'ready'}],
                message_info={'content': 'Hello %s' % self.test_partner.name,
                              'mail_mail_values': {
                                'author_id': self.env.user.partner_id,
                              },
                              'message_type': 'auto_comment',
                              'subtype': 'mail.mt_comment',
                             }
            ):
            self.action.with_context(self.context).run()
        # NOTE: template using current user will have funny email_from
        self.assertEqual(self.test_partner.message_ids[0].email_from, self.partner_root.email_formatted)
        self.assertFalse(self.test_partner.message_partner_ids)

        # test with autofollow and note
        self.action.write({
            'mail_post_autofollow': True,
            'mail_post_method': 'note'
        })
        with self.assertSinglePostNotifications(
                [{'partner': self.test_partner, 'type': 'email', 'status': 'ready'}],
                message_info={'content': 'Hello %s' % self.test_partner.name,
                              'message_type': 'auto_comment',
                              'subtype': 'mail.mt_note',
                             }
            ):
            self.action.with_context(self.context).run()
        self.assertEqual(len(self.test_partner.message_ids), 3,
                         '2 new messages produced')
        self.assertEqual(self.test_partner.message_partner_ids, self.test_partner)

    def test_action_next_activity(self):
        self.action.write({
            'state': 'next_activity',
            'activity_user_type': 'specific',
            'activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
            'activity_summary': 'TestNew',
        })
        before_count = self.env['mail.activity'].search_count([])
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create next activity action correctly finished should return False')
        self.assertEqual(self.env['mail.activity'].search_count([]), before_count + 1)
        self.assertEqual(self.env['mail.activity'].search_count([('summary', '=', 'TestNew')]), 1)

    def test_action_next_activity_warning(self):
        self.action.write({
            'state': 'next_activity',
            'activity_user_type': 'generic',
            "activity_user_field_name": "user_id.name",
            'activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
            'activity_summary': 'TestNew',
        })
        self.assertEqual(self.action.warning, "The field 'Salesperson > Name' is not a user field.")
        self.action.write({"activity_user_field_name": "parent_id.user_id"})
        self.assertEqual(self.action.warning, False)

    def test_action_next_activity_due_date(self):
        """ Make sure we don't crash if a due date is set without a type. """
        self.action.write({
            'state': 'next_activity',
            'activity_user_type': 'specific',
            'activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
            'activity_summary': 'TestNew',
            'activity_date_deadline_range': 1,
            'activity_date_deadline_range_type': False,
        })
        before_count = self.env['mail.activity'].search_count([])
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create next activity action correctly finished should return False')
        self.assertEqual(self.env['mail.activity'].search_count([]), before_count + 1)
        self.assertEqual(self.env['mail.activity'].search_count([('summary', '=', 'TestNew')]), 1)

    def test_action_next_activity_from_x2m_user(self):
        self.test_partner.user_ids = self.user_demo | self.user_admin
        self.action.write({
            'state': 'next_activity',
            'activity_user_type': 'generic',
            'activity_user_field_name': 'user_ids',
            'activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
            'activity_summary': 'TestNew',
        })
        before_count = self.env['mail.activity'].search_count([])
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create next activity action correctly finished should return False')
        self.assertEqual(self.env['mail.activity'].search_count([]), before_count + 1)
        self.assertRecordValues(
            self.env['mail.activity'].search([('res_model', '=', 'res.partner'), ('res_id', '=', self.test_partner.id)]),
            [{
                'summary': 'TestNew',
                'user_id': self.user_demo.id,  # the first user found
            }],
        )

    def test_action_next_activity_formview(self):
        email_activity_type = self.env.ref('mail.mail_activity_data_email')
        email_activity_type.write({'default_note': '<p>Default note for email</p>'})
        with Form(self.env['ir.actions.server'], view='base.view_server_action_form') as f:
            self.assertEqual(f.name, '')
            f.model_id = self.res_partner_model
            f.state = 'next_activity'
            self.assertTrue(f._get_modifier('activity_plan_id', 'invisible'))
            self.assertEqual(f.name, 'Create Activity')
            self.assertTrue(f._get_modifier('activity_type_id', 'required'))
            f.activity_type_id = self.env.ref('mail.mail_activity_data_todo')
            self.assertEqual(f.name, 'Create To-Do')
            self.assertEqual(f.activity_summary, 'To-Do')
            self.assertEqual(f.activity_date_deadline_range, 1)
            self.assertEqual(f.activity_date_deadline_range_type, 'days')
            self.assertEqual(f.activity_user_type, 'specific')
            self.assertFalse(f.activity_user_id)
            self.assertFalse(f.activity_note)
            f.activity_summary = 'Send a wonderful email'
            f.activity_note = 'Hello world'
            f.activity_date_deadline_range = 3
            f.activity_date_deadline_range_type = 'weeks'
            f.activity_user_id = self.user_demo
            f.activity_type_id = email_activity_type
            self.assertEqual(f.activity_summary, 'Email', 'activity_summary should be changed to "Email"')
            self.assertEqual(f.activity_note, '<p>Default note for email</p>', 'activity_note should be changed to default note of email activity')
            self.assertEqual(f.activity_date_deadline_range, 3)
            self.assertEqual(f.activity_date_deadline_range_type, 'weeks')
            self.assertEqual(f.activity_type_id, email_activity_type)
            self.assertEqual(f.activity_user_type, 'specific')
            self.assertEqual(f.activity_user_id, self.user_demo)
            f.activity_user_type = 'generic'
            self.assertFalse(f.activity_user_id)
            self.assertEqual(f.activity_user_field_name, 'user_id')
            f.activity_type_id = self.env.ref('mail.mail_activity_data_call')
            self.assertEqual(f.activity_type_id, self.env.ref('mail.mail_activity_data_call'))
            self.assertEqual(f.activity_user_type, 'generic')
            self.assertEqual(f.activity_user_field_name, 'user_id')
            self.assertEqual(f.activity_summary, 'Call')
            self.assertFalse(f.activity_note, 'activity_note should be changed to default note of call activity (which is empty)')
            self.assertEqual(f.activity_date_deadline_range, 3)
            self.assertEqual(f.activity_date_deadline_range_type, 'weeks')

    def test_action_next_activity_formview_with_plans(self):
        activity_type_todo = self.env.ref('mail.mail_activity_data_todo')
        admin_activity_plan = self.env['mail.activity.plan'].create({
            'name': 'Test Onboarding Plan (responsible: admin)',
            'res_model': 'res.partner',
            'template_ids': [
                Command.create({
                    'activity_type_id': activity_type_todo.id,
                    'responsible_id': self.user_admin.id,
                    'responsible_type': 'other',
                    'sequence': 10,
                    'summary': 'Plan training',
                }), Command.create({
                    'activity_type_id': activity_type_todo.id,
                    'responsible_id': self.user_admin.id,
                    'responsible_type': 'other',
                    'sequence': 20,
                    'summary': 'Training',
                }),
            ]
        })
        on_demand_activity_plan = self.env['mail.activity.plan'].create({
            'name': 'Test Onboarding Plan (responsible: on demand)',
            'res_model': 'res.partner',
            'template_ids': [
                Command.create({
                    'activity_type_id': activity_type_todo.id,
                    'delay_count': 3,
                    'delay_from': 'before_plan_date',
                    'delay_unit': 'days',
                    'responsible_id': self.user_admin.id,
                    'responsible_type': 'other',
                    'sequence': 10,
                    'summary': 'Plan training',
                }), Command.create({
                    'activity_type_id': activity_type_todo.id,
                    'delay_count': 2,
                    'delay_from': 'after_plan_date',
                    'delay_unit': 'weeks',
                    'responsible_type': 'on_demand',
                    'sequence': 20,
                    'summary': 'Training',
                }),
            ]
        })
        self.test_partner.write({'user_id': self.user_employee.id})
        with Form(self.env['ir.actions.server'], view='base.view_server_action_form') as f:
            self.assertEqual(f.name, '')
            self.assertTrue(f._get_modifier('activity_plan_id', 'invisible'))
            f.model_id = self.res_partner_model
            f.state = 'next_activity'
            self.assertFalse(f._get_modifier('activity_plan_id', 'invisible'))
            f.activity_user_id = self.user_admin
            f.activity_type_id = self.env.ref('mail.mail_activity_data_todo')
            f.activity_summary = 'Should be overridden by plan'
            f.activity_note = 'Should be overridden by plan'
            f.activity_date_deadline_range = 2
            f.activity_date_deadline_range_type = 'weeks'
            f.activity_plan_id = admin_activity_plan
            self.assertEqual(f.activity_date_deadline_range, 2)
            self.assertEqual(f.activity_date_deadline_range_type, 'weeks')
            self.assertFalse(f.activity_type_id)
            self.assertFalse(f._get_modifier('activity_type_id', 'invisible'))
            self.assertTrue(f._get_modifier('activity_summary', 'invisible'))
            self.assertFalse(f.activity_summary)
            self.assertTrue(f._get_modifier('activity_note', 'invisible'))
            self.assertFalse(f.activity_note)
            self.assertTrue(f._get_modifier('activity_user_type', 'invisible'))
            self.assertFalse(f.activity_user_type)
            self.assertTrue(f._get_modifier('activity_user_id', 'invisible'))
            self.assertFalse(f.activity_user_id)
            self.assertTrue(f._get_modifier('activity_user_field_name', 'invisible'))
            self.assertFalse(f.activity_user_field_name)
            self.assertEqual(f.name, 'Plan activities: Test Onboarding Plan (responsible: admin)')

            f.activity_plan_id = on_demand_activity_plan
            self.assertEqual(f.name, 'Plan activities: Test Onboarding Plan (responsible: on demand)')
            self.assertEqual(f.activity_user_type, 'specific')
            self.assertTrue(f._get_modifier('activity_user_field_name', 'invisible'))
            f.activity_user_type = 'generic'
            self.assertTrue(f._get_modifier('activity_user_id', 'invisible'))
            f.activity_user_field_name = 'user_id'
            action = f.save()

        before_count = self.env['mail.activity'].search_count([])
        now = self.env.cr._now
        run_res = action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create next activity action correctly finished should return False')
        self.assertEqual(self.env['mail.activity'].search_count([]), before_count + 2)
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', self.test_partner.id),
        ]).grouped('user_id')
        self.assertRecordValues(activities[self.user_admin], [
            {
                'activity_type_id': activity_type_todo.id,
                'summary': 'Plan training',
                'date_deadline': (now + timedelta(days=11)).date(),
            }
        ])
        self.assertRecordValues(activities[self.user_employee], [
            {
                'activity_type_id': activity_type_todo.id,
                'summary': 'Training',
                'date_deadline': (now + timedelta(weeks=4)).date(),
            }
        ])

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_action_send_mail_without_mail_thread(self):
        """ Check running a server action to send an email with custom layout on a non mail.thread model """
        no_thread_record = self.env['mail.test.nothread'].create({'name': 'Test NoMailThread', 'customer_id': self.test_partner.id})
        no_thread_template = self._create_template(
            'mail.test.nothread',
            {
                'email_from': 'someone@example.com',
                'partner_to': '{{ object.customer_id.id }}',
                'subject': 'About {{ object.name }}',
                'body_html': '<p>Hello <t t-out="object.name"/></p>',
                'email_layout_xmlid': 'mail.mail_notification_layout',
            }
        )

        # update action: send an email
        self.action.write({
            'mail_post_method': 'email',
            'state': 'mail_post',
            'model_id': self.env['ir.model'].search([('model', '=', 'mail.test.nothread')], limit=1).id,
            'model_name': 'mail.test.nothread',
            'template_id': no_thread_template.id,
        })

        with self.mock_mail_gateway(), self.mock_mail_app():
            action_ctx = {
                'active_model': 'mail.test.nothread',
                'active_id': no_thread_record.id,
            }
            self.action.with_context(action_ctx).run()

        mail = self.assertMailMail(
            self.test_partner,
            None,
            content='Hello Test NoMailThread',
            fields_values={
                'email_from': 'someone@example.com',
                'subject': 'About Test NoMailThread',
            }
        )
        self.assertNotIn('Powered by', mail.body_html, 'Body should contain the notification layout')
