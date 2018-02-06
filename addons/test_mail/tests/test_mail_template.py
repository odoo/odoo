# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime, timedelta

from odoo.addons.test_mail.tests.common import BaseFunctionalTest, MockEmails, TestRecipients
from odoo.tools import mute_logger, DEFAULT_SERVER_DATETIME_FORMAT


class TestMailTemplate(BaseFunctionalTest, MockEmails, TestRecipients):

    def setUp(self):
        super(TestMailTemplate, self).setUp()

        self.user_employee.write({
            'groups_id': [(4, self.env.ref('base.group_partner_manager').id)],
        })

        self._attachments = [{
            'name': '_Test_First',
            'datas_fname': 'first.txt',
            'datas': base64.b64encode(b'My first attachment'),
            'res_model': 'res.partner',
            'res_id': self.user_admin.partner_id.id
        }, {
            'name': '_Test_Second',
            'datas_fname': 'second.txt',
            'datas': base64.b64encode(b'My second attachment'),
            'res_model': 'res.partner',
            'res_id': self.user_admin.partner_id.id
        }]

        self.email_1 = 'test1@example.com'
        self.email_2 = 'test2@example.com'
        self.email_3 = self.partner_1.email
        self.email_template = self.env['mail.template'].create({
            'model_id': self.env['ir.model']._get('mail.test.simple').id,
            'name': 'Pigs Template',
            'subject': '${object.name}',
            'body_html': '${object.email_from}',
            'user_signature': False,
            'attachment_ids': [(0, 0, self._attachments[0]), (0, 0, self._attachments[1])],
            'partner_to': '%s,%s' % (self.partner_2.id, self.user_admin.partner_id.id),
            'email_to': '%s, %s' % (self.email_1, self.email_2),
            'email_cc': '%s' % self.email_3})

        # admin should receive emails
        self.user_admin.write({'notification_type': 'email'})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_w_template(self):
        composer = self.env['mail.compose.message'].sudo(self.user_employee).with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.test.simple',
            'default_res_id': self.test_record.id,
            'default_template_id': self.email_template.id,
        }).create({'subject': 'Forget me subject', 'body': 'Dummy body'})

        # perform onchange and send emails
        values = composer.onchange_template_id(self.email_template.id, 'comment', self.test_record._name, self.test_record.id)['value']
        composer.write(values)
        composer.send_mail()

        new_partners = self.env['res.partner'].search([('email', 'in', [self.email_1, self.email_2])])
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [new_partners[0]], [new_partners[1]], [self.partner_admin]],
            subject=self.test_record.name,
            body_content=self.test_record.email_from,
            attachments=[('first.txt', b'My first attachment', 'text/plain'), ('second.txt', b'My second attachment', 'text/plain')])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_post_w_template(self):
        self.test_record.sudo(self.user_employee).message_post_with_template(self.email_template.id, composition_mode='comment')

        new_partners = self.env['res.partner'].search([('email', 'in', [self.email_1, self.email_2])])
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [new_partners[0]], [new_partners[1]], [self.partner_admin]],
            subject=self.test_record.name,
            body_content=self.test_record.email_from,
            attachments=[('first.txt', b'My first attachment', 'text/plain'), ('second.txt', b'My second attachment', 'text/plain')])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_w_template_mass_mailing(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._quick_create_ctx).create({'name': 'Test2', 'email_from': 'laurie.poiret@example.com'})

        composer = self.env['mail.compose.message'].sudo(self.user_employee).with_context({
            'default_composition_mode': 'mass_mail',
            # 'default_notify': True,
            'default_notify': False,
            'default_model': 'mail.test.simple',
            'default_res_id': self.test_record.id,
            'default_template_id': self.email_template.id,
            'active_ids': [self.test_record.id, test_record_2.id]
        }).create({})
        values = composer.onchange_template_id(self.email_template.id, 'mass_mail', 'mail.test.simple', self.test_record.id)['value']
        composer.write(values)
        composer.send_mail()

        new_partners = self.env['res.partner'].search([('email', 'in', [self.email_1, self.email_2])])
        # hack to use assertEmails
        self._mails_record1 = [dict(mail) for mail in self._mails if '%s-%s' % (self.test_record.id, self.test_record._name) in mail['message_id']]
        self._mails_record2 = [dict(mail) for mail in self._mails if '%s-%s' % (test_record_2.id, test_record_2._name) in mail['message_id']]

        self._mails = self._mails_record1
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [new_partners[0]], [new_partners[1]], [self.partner_admin]],
            subject=self.test_record.name,
            body_content=self.test_record.email_from,
            attachments=[('first.txt', b'My first attachment', 'text/plain'), ('second.txt', b'My second attachment', 'text/plain')])

        self._mails = self._mails_record2
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [new_partners[0]], [new_partners[1]], [self.partner_admin]],
            subject=test_record_2.name,
            body_content=test_record_2.email_from,
            attachments=[('first.txt', b'My first attachment', 'text/plain'), ('second.txt', b'My second attachment', 'text/plain')])

        message_1 = self.test_record.message_ids[0]
        message_2 = test_record_2.message_ids[0]

        # messages effectively posted
        self.assertEqual(message_1.subject, self.test_record.name)
        self.assertEqual(message_2.subject, test_record_2.name)
        self.assertIn(self.test_record.email_from, message_1.body)
        self.assertIn(test_record_2.email_from, message_2.body)

    def test_composer_template_save(self):
        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.test.simple',
            'default_res_id': self.test_record.id,
        }).create({
            'subject': 'Forget me subject',
            'body': '<p>Dummy body</p>'
        }).save_as_template()
        # Test: email_template subject, body_html, model
        last_template = self.env['mail.template'].search([('model', '=', 'mail.test.simple'), ('subject', '=', 'Forget me subject')], limit=1)
        self.assertEqual(last_template.body_html, '<p>Dummy body</p>', 'email_template incorrect body_html')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_send_email(self):
        mail_id = self.email_template.send_mail(self.test_record.id)
        mail = self.env['mail.mail'].browse(mail_id)
        self.assertEqual(mail.subject, self.test_record.name)
        self.assertEqual(mail.email_to, self.email_template.email_to)
        self.assertEqual(mail.email_cc, self.email_template.email_cc)
        self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)

    def test_template_add_context_action(self):
        self.email_template.create_action()

        # check template act_window has been updated
        self.assertTrue(bool(self.email_template.ref_ir_act_window))

        # check those records
        action = self.email_template.ref_ir_act_window
        self.assertEqual(action.name, 'Send Mail (%s)' % self.email_template.name)
        self.assertEqual(action.binding_model_id.model, 'mail.test.simple')

    # def test_template_scheduled_date(self):
    #     from unittest.mock import patch

    #     self.email_template_in_2_days = self.email_template.copy()

    #     with patch('odoo.addons.mail.tests.test_mail_template.datetime', wraps=datetime) as mock_datetime:
    #         mock_datetime.now.return_value = datetime(2017, 11, 15, 11, 30, 28)
    #         mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

    #         self.email_template_in_2_days.write({
    #             'scheduled_date': "${(datetime.datetime.now() + relativedelta(days=2)).strftime('%s')}" % DEFAULT_SERVER_DATETIME_FORMAT,
    #         })

    #         mail_now_id = self.email_template.send_mail(self.test_record.id)
    #         mail_in_2_days_id = self.email_template_in_2_days.send_mail(self.test_record.id)

    #         mail_now = self.env['mail.mail'].browse(mail_now_id)
    #         mail_in_2_days = self.env['mail.mail'].browse(mail_in_2_days_id)

    #         # mail preparation
    #         self.assertEqual(mail_now.exists() | mail_in_2_days.exists(), mail_now | mail_in_2_days)
    #         self.assertEqual(bool(mail_now.scheduled_date), False)
    #         self.assertEqual(mail_now.state, 'outgoing')
    #         self.assertEqual(mail_in_2_days.state, 'outgoing')
    #         scheduled_date = datetime.strptime(mail_in_2_days.scheduled_date, DEFAULT_SERVER_DATETIME_FORMAT)
    #         date_in_2_days = datetime.now() + timedelta(days = 2)
    #         self.assertEqual(scheduled_date, date_in_2_days)
    #         # self.assertEqual(scheduled_date.month, date_in_2_days.month)
    #         # self.assertEqual(scheduled_date.year, date_in_2_days.year)

    #         # Launch the scheduler on the first mail, it should be reported in self.mails
    #         # and the mail_mail is now deleted
    #         self.env['mail.mail'].process_email_queue()
    #         self.assertEqual(mail_now.exists() | mail_in_2_days.exists(), mail_in_2_days)

    #         # Launch the scheduler on the first mail, it's still in 'outgoing' state
    #         self.env['mail.mail'].process_email_queue(ids=[mail_in_2_days.id])
    #         self.assertEqual(mail_in_2_days.state, 'outgoing')
    #         self.assertEqual(mail_now.exists() | mail_in_2_days.exists(), mail_in_2_days)
