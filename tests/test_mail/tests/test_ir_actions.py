# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.test_ir_actions import TestServerActionsBase
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged
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
                              'fields_values': {
                                'author_id': self.env.user.partner_id,
                              },
                              'message_type': 'notification',
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
                              'message_type': 'notification',
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
