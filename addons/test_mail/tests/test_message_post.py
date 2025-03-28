# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from datetime import datetime, timedelta
from freezegun import freeze_time
from itertools import product
from markupsafe import escape, Markup
from unittest.mock import patch

from odoo import tools
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE_PLAINTEXT
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.api import call_kw
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger, formataddr
from odoo.tests.common import users


class TestMessagePostCommon(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMessagePostCommon, cls).setUpClass()

        # portal user, notably for ACLS / notifications
        cls.user_portal = cls._create_portal_user()
        cls.partner_portal = cls.user_portal.partner_id

        # another standard employee to test follow and notifications between two
        # users (and not admin / user)
        cls.user_employee_2 = mail_new_test_user(
            cls.env, login='employee2',
            groups='base.group_user',
            company_id=cls.company_admin.id,
            email='eglantine@example.com',  # check: use a formatted email
            name='Eglantine Employee2',
            notification_type='email',
            signature='--\nEglantine',
        )
        cls.partner_employee_2 = cls.user_employee_2.partner_id

        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com'
        })
        cls._reset_mail_context(cls.test_record)
        cls.test_message = cls.env['mail.message'].create({
            'author_id': cls.partner_employee.id,
            'body': '<p>Notify Body <span>Woop Woop</span></p>',
            'email_from': cls.partner_employee.email_formatted,
            'is_internal': False,
            'message_id': tools.mail.generate_tracking_message_id('dummy-generate'),
            'message_type': 'comment',
            'model': cls.test_record._name,
            'record_name': False,
            'reply_to': 'wrong.alias@test.example.com',
            'subtype_id': cls.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            'subject': 'Notify Test',
        })
        cls.user_admin.write({'notification_type': 'email'})

    def setUp(self):
        super(TestMessagePostCommon, self).setUp()
        # patch registry to simulate a ready environment; see ``_message_auto_subscribe_notify``
        self.patch(self.env.registry, 'ready', True)


@tagged('mail_post')
class TestMailNotifyAPI(TestMessagePostCommon):

    @mute_logger('odoo.models.unlink')
    @users('employee')
    def test_email_notifiction_layouts(self):
        self.user_employee.write({'notification_type': 'email'})
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)
        test_message = self.env['mail.message'].browse(self.test_message.ids)

        recipients_data = self._generate_notify_recipients(self.partner_1 + self.partner_2 + self.partner_employee)
        for email_xmlid in ['mail.mail_notification_light',
                            'mail.mail_notification_layout',
                            'mail.mail_notification_layout_with_responsible_signature']:
            test_message.sudo().notification_ids.unlink()  # otherwise partner/message constraint fails
            test_message.write({'email_layout_xmlid': email_xmlid})
            with self.mock_mail_gateway():
                test_record._notify_thread_by_email(
                    test_message,
                    recipients_data,
                    force_send=False
                )
            self.assertEqual(len(self._new_mails), 2, 'Should have 2 emails: one for customers, one for internal users')

            # check customer email
            customer_email = self._new_mails.filtered(lambda mail: mail.recipient_ids == self.partner_1 + self.partner_2)
            self.assertTrue(customer_email)

            # check internal user email
            user_email = self._new_mails.filtered(lambda mail: mail.recipient_ids == self.partner_employee)
            self.assertTrue(user_email)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_notify_by_mail_add_signature(self):
        test_track = self.env['mail.test.track'].with_context(self._test_context).with_user(self.user_employee).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com'
        })
        test_track.user_id = self.env.user

        signature = self.env.user.signature

        template = self.env.ref('mail.mail_notification_layout_with_responsible_signature', raise_if_not_found=True).sudo()
        self.assertIn("record.user_id.sudo().signature", template.arch)

        with self.mock_mail_gateway():
            test_track.message_post(
                body="Test body",
                email_add_signature=True,
                email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                mail_auto_delete=False,
                partner_ids=[self.partner_1.id, self.partner_2.id],
            )
        found_mail = self._new_mails
        self.assertIn(signature, found_mail.body_html)
        self.assertEqual(found_mail.body_html.count(signature), 1)

        with self.mock_mail_gateway():
            test_track.message_post(
                body="Test body",
                email_add_signature=False,
                email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                mail_auto_delete=False,
                partner_ids=[self.partner_1.id, self.partner_2.id],
            )
        found_mail = self._new_mails
        self.assertNotIn(signature, found_mail.body_html)
        self.assertEqual(found_mail.body_html.count(signature), 0)

    @users('employee')
    def test_notify_by_email_add_signature_no_author_user_or_no_user(self):
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)
        test_message = self.env['mail.message'].browse(self.test_message.ids)
        test_message.write({
            'author_id': self.env['res.partner'].sudo().create({
                'name': 'Steve',
            }).id
        })
        # TOFIX: the test is actually broken because test_message cannot be
        # read; this populates the cache to make it work, but that's cheating...
        test_message.sudo().email_add_signature
        template_values = test_record._notify_by_email_prepare_rendering_context(test_message, {})
        self.assertNotEqual(escape(template_values['signature']), escape('<p>-- <br/>Steve</p>'))

        self.test_message.author_id = None
        template_values = test_record._notify_by_email_prepare_rendering_context(test_message, {})
        self.assertEqual(template_values['signature'], '')

    @users('employee')
    def test_notify_by_email_prepare_rendering_context(self):
        """ Verify that the template context company value is right
        after switching the env company or if a company_id is set
        on mail record.
        """
        current_user = self.env.user
        main_company = current_user.company_id
        other_company = self.env['res.company'].with_user(self.user_admin).create({'name': 'Company B'})
        current_user.sudo().write({'company_ids': [(4, other_company.id)]})
        test_record = self.env['mail.test.multi.company'].with_user(self.user_admin).create({
            'name': 'Multi Company Record',
            'company_id': False,
        })

        # self.env.company.id = Main Company    AND    test_record.company_id = False
        self.assertEqual(self.env.company.id, main_company.id)
        self.assertEqual(test_record.company_id.id, False)
        template_values = test_record._notify_by_email_prepare_rendering_context(test_record.message_ids, {})
        self.assertEqual(template_values.get('company').id, self.env.company.id)

        # self.env.company.id = Other Company    AND    test_record.company_id = False
        current_user.company_id = other_company
        test_record = self.env['mail.test.multi.company'].browse(test_record.id)
        self.assertEqual(self.env.company.id, other_company.id)
        self.assertEqual(test_record.company_id.id, False)
        template_values = test_record._notify_by_email_prepare_rendering_context(test_record.message_ids, {})
        self.assertEqual(template_values.get('company').id, self.env.company.id)

        # self.env.company.id = Other Company    AND    test_record.company_id = Main Company
        test_record.company_id = main_company
        test_record = self.env['mail.test.multi.company'].browse(test_record.id)
        self.assertEqual(self.env.company.id, other_company.id)
        self.assertEqual(test_record.company_id.id, main_company.id)
        template_values = test_record._notify_by_email_prepare_rendering_context(test_record.message_ids, {})
        self.assertEqual(template_values.get('company').id, main_company.id)

    @users('employee')
    def test_notify_recipients_internals(self):
        base_record = self.test_record.with_env(self.env)
        pdata = self._generate_notify_recipients(self.partner_1 | self.partner_employee)
        msg_vals = {
            'body': 'Message body',
            'model': base_record._name,
            'res_id': base_record.id,
            'subject': 'Message subject',
        }
        link_vals = {
            'token': 'token_val',
            'access_token': 'access_token_val',
            'auth_signup_token': 'auth_signup_token_val',
            'auth_login': 'auth_login_val',
        }
        notify_msg_vals = dict(msg_vals, **link_vals)

        # test notifying the class (void recordset)
        classify_res = self.env[base_record._name]._notify_get_recipients_classify(
            self.env['mail.message'], pdata, 'My Custom Model Name',
            msg_vals=notify_msg_vals,
        )
        # find back information for each recipients
        partner_info = next(item for item in classify_res if item['recipients'] == self.partner_1.ids)
        emp_info = next(item for item in classify_res if item['recipients'] == self.partner_employee.ids)
        # partner: no access button
        self.assertFalse(partner_info['has_button_access'])
        # employee: access button and link
        self.assertTrue(emp_info['has_button_access'])
        for param, value in link_vals.items():
            self.assertIn(f'{param}={value}', emp_info['button_access']['url'])
        self.assertIn(f'model={base_record._name}', emp_info['button_access']['url'])
        self.assertIn(f'res_id={base_record.id}', emp_info['button_access']['url'])
        self.assertNotIn('body', emp_info['button_access']['url'])
        self.assertNotIn('subject', emp_info['button_access']['url'])

        # test when notifying on non-records (e.g. MailThread._message_notify())
        for model, res_id in ((base_record._name, False),
                              (base_record._name, 0),  # browse(0) does not return a valid recordset
                              ('mail.thread', False),
                              ('mail.thread', base_record.id)):
            with self.subTest(model=model, res_id=res_id):
                notify_msg_vals.update({
                    'model': model,
                    'res_id': res_id,
                })
                classify_res = self.env[model].browse(res_id)._notify_get_recipients_classify(
                    self.env['mail.message'], pdata, 'Test',
                    msg_vals=notify_msg_vals,
                )
                # find back information for partner
                partner_info = next(item for item in classify_res if item['recipients'] == self.partner_1.ids)
                emp_info = next(item for item in classify_res if item['recipients'] == self.partner_employee.ids)
                # check there is no access button
                self.assertFalse(partner_info['has_button_access'])
                self.assertFalse(emp_info['has_button_access'])

        # test when notifying based a valid record, but asking for a falsy record in msg_vals
        for model, res_id in ((base_record._name, False),
                              (base_record._name, 0),  # browse(0) does not return a valid recordset
                              (False, base_record.id),
                              (False, False),
                              ('mail.thread', False),
                              ('mail.thread', base_record.id)):
            with self.subTest(model=model, res_id=res_id):
                # note that msg_vals wins over record on which method is called
                notify_msg_vals.update({
                    'model': model,
                    'res_id': res_id,
                })
                classify_res = base_record._notify_get_recipients_classify(
                    self.env['mail.message'], pdata, 'Test',
                    msg_vals=notify_msg_vals,
                )
                # find back information for partner
                partner_info = next(item for item in classify_res if item['recipients'] == self.partner_1.ids)
                emp_info = next(item for item in classify_res if item['recipients'] == self.partner_employee.ids)
                # check there is no access button
                self.assertFalse(partner_info['has_button_access'])
                self.assertFalse(emp_info['has_button_access'])

    @users('employee_c2')
    def test_notify_reply_to_computation_mc(self):
        """ Test reply-to computation in multi company mode. Add notably tests
        depending on user and records company_id / company_ids. """

        # Test1: no company_id field: depends on current user browsing
        test_record = self.test_record.with_env(self.env)
        self.assertEqual(
            test_record._notify_get_reply_to()[test_record.id],
            formataddr((
                f"{self.user_employee_c2.company_id.name} {test_record.name}",
                f"{self.alias_catchall_c2}@{self.alias_domain_c2_name}"))
        )
        test_record_c1 = test_record.with_user(self.user_employee)
        self.assertEqual(
            test_record_c1._notify_get_reply_to()[test_record_c1.id],
            formataddr((
                f"{self.user_employee.company_id.name} {test_record_c1.name}",
                f"{self.alias_catchall}@{self.alias_domain}"))
        )

        # Test2: MC environment get default value from env
        self.user_employee_c2.write({'company_ids': [(4, self.user_employee.company_id.id)]})
        test_records = self.env['mail.test.multi.company'].create([
            {'name': 'Test',
             'company_id': self.user_employee.company_id.id},
            {'name': 'Test',
             'company_id': self.user_employee_c2.company_id.id},
        ])
        res = test_records._notify_get_reply_to()
        for test_record in test_records:
            company = test_record.company_id
            if company == self.company_2:
                alias_domain = self.alias_domain_c2_name
                alias_catchall = self.alias_catchall_c2
            else:
                alias_domain = self.alias_domain
                alias_catchall = self.alias_catchall

            self.assertEqual(
                res[test_record.id],
                formataddr((f"{company.name} {test_record.name}", f"{alias_catchall}@{alias_domain}"))
            )

        # Test3: get company from record (company_id field)
        self.user_employee_c2.write({'company_ids': [(4, self.company_3.id)]})
        test_records = self.env['mail.test.multi.company'].create([
            {'name': 'Test1',
            'company_id': self.company_3.id},
            {'name': 'Test2',
            'company_id': self.company_3.id},
        ])
        res = test_records._notify_get_reply_to()
        for test_record in test_records:
            self.assertEqual(
                res[test_record.id],
                formataddr((
                    f"{self.company_3.name} {test_record.name}",
                    f"{self.alias_catchall_c3}@{self.alias_domain_c3_name}"))
            )


@tagged('mail_post', 'mail_notify')
class TestMessageNotify(TestMessagePostCommon):

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_notify(self):
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)

        with self.assertSinglePostNotifications(
            [{'partner': self.partner_1, 'type': 'email',},
             {'partner': self.partner_admin, 'type': 'email',},
             {'partner': self.partner_employee_2, 'type': 'email',},
            ], message_info={
                'content': '<p>You have received a notification</p>',
                'message_type': 'user_notification',
                'message_values': {
                    'author_id': self.partner_employee,
                    'body': '<p>You have received a notification</p>',
                    'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                    'message_type': 'user_notification',
                    'model': test_record._name,
                    'notified_partner_ids': self.partner_1 | self.partner_employee_2 | self.partner_admin,
                    'res_id': test_record.id,
                    'subtype_id': self.env.ref('mail.mt_note'),
                },
                'subtype': 'mail.mt_note',
            },
        ):
            new_notification = test_record.message_notify(
                body=Markup('<p>You have received a notification</p>'),
                partner_ids=[self.partner_1.id, self.partner_admin.id, self.partner_employee_2.id],
                subject='This should be a subject',
            )
        self.assertNotIn(new_notification, self.test_record.message_ids)

        # notified_partner_ids should be empty after copying the message
        copy = new_notification.copy()
        self.assertFalse(copy.notified_partner_ids)

        admin_mails = [mail for mail in self._mails if self.partner_admin.name in mail.get('email_to')[0]]
        self.assertEqual(len(admin_mails), 1, 'There should be exactly one email sent to admin')
        admin_mail_body = admin_mails[0].get('body')

        self.assertTrue('model=' in admin_mail_body, 'The email sent to admin should contain an access link')
        admin_access_link = admin_mail_body[
            admin_mail_body.index('model='):admin_mail_body.index('/>', admin_mail_body.index('model=')) - 1]
        self.assertIn(f'model={self.test_record._name}', admin_access_link, 'The access link should contain a valid model argument')
        self.assertIn(f'res_id={self.test_record.id}', admin_access_link, 'The access link should contain a valid res_id argument')

        partner_mails = [x for x in self._mails if self.partner_1.name in x.get('email_to')[0]]
        self.assertEqual(len(partner_mails), 1, 'There should be exactly one email sent to partner')
        partner_mail_body = partner_mails[0].get('body')
        self.assertNotIn('/mail/view?model=', partner_mail_body, 'The email sent to customer should not contain an access link')

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_notify_author(self):
        """ Author is not added in notified people by default, unless asked to
        using the 'notify_author' parameter or context key. """
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)

        with self.mock_mail_gateway():
            new_notification = test_record.message_notify(
                body=Markup('<p>You have received a notification</p>'),
                partner_ids=(self.partner_1 + self.partner_employee).ids,
                subject='This should be a subject',
            )

        self.assertEqual(new_notification.notified_partner_ids, self.partner_1)

        with self.mock_mail_gateway():
            new_notification = test_record.message_notify(
                body=Markup('<p>You have received a notification</p>'),
                notify_author=True,
                partner_ids=(self.partner_1 + self.partner_employee).ids,
                subject='This should be a subject',
            )

        self.assertEqual(
            new_notification.notified_partner_ids,
            self.partner_1 + self.partner_employee,
            'Notify: notify_author parameter skips the author restriction'
        )

        with self.mock_mail_gateway():
            new_notification = test_record.with_context(mail_notify_author=True).message_notify(
                body=Markup('<p>You have received a notification</p>'),
                partner_ids=(self.partner_1 + self.partner_employee).ids,
                subject='This should be a subject',
            )

        self.assertEqual(
            new_notification.notified_partner_ids,
            self.partner_1 + self.partner_employee,
            'Notify: mail_notify_author context key skips the author restriction'
        )

    @users('employee')
    def test_notify_batch(self):
        """ Test notify in batch. Currently not supported. """
        test_records, _partners = self._create_records_for_batch('mail.test.simple', 10)

        with self.assertRaises(ValueError):
            test_records.message_notify(
                body=Markup('<p>Nice notification content</p>'),
                partner_ids=self.partner_employee_2.ids,
                subject='Notify Subject',
            )

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_notify_from_user_id(self):
        """ Test notify coming from user_id assignment (in batch) """
        test_records, _ = self._create_records_for_batch(
            'mail.test.track', 10, {
                'company_id': self.env.user.company_id.id,
                'email_from': self.env.user.email_formatted,
                'user_id': False,
            }
        )
        test_records = self.env['mail.test.track'].browse(test_records.ids)
        self.flush_tracking()

        with self.mock_mail_gateway(), self.mock_mail_app():
            test_records.write({'user_id': self.user_employee_2.id})
            self.flush_tracking()

        self.assertEqual(len(self._new_msgs), 20, 'Should have 20 messages: 10 tracking and 10 assignments')
        model_name = self.env['ir.model'].sudo()._get(test_records._name).name
        for test_record in test_records:
            assign_notif = self._new_msgs.filtered(lambda msg: msg.message_type == 'user_notification' and msg.res_id == test_record.id)
            self.assertTrue(assign_notif)
            self.assertMailNotifications(
                assign_notif,
                [{
                    'content': f'You have been assigned to the {model_name}',
                    'email_values': {
                        # used to distinguished outgoing emails
                        'subject': f'You have been assigned to {test_record.name}',
                    },
                    'message_type': 'user_notification',
                    'message_values': {
                        'author_id': self.partner_employee,
                        'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                        'model': test_record._name,
                        'notified_partner_ids': self.partner_employee_2,
                        'res_id': test_record.id,
                    },
                    'notif': [
                        {'partner': self.partner_employee_2, 'type': 'email',},
                    ],
                    'subtype': 'mail.mt_note',
                }],
            )

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_notify_parameters(self):
        """ Test usage of parameters in notify, both for unwanted side effects
        and magic parameters. """
        test_record = self.test_record.with_env(self.env)

        for parameters in [
            {'message_type': 'comment'},
            {'child_ids': []},
            {'mail_ids': []},
            {'notification_ids': []},
            {'notified_partner_ids': []},
            {'reaction_ids': []},
            {'starred_partner_ids': []},
        ]:
            with self.subTest(parameters=parameters), \
                 self.mock_mail_gateway(), \
                 self.assertRaises(ValueError):
                _new_message = test_record.message_notify(
                    body=Markup('<p>You will not receive a notification</p>'),
                    partner_ids=self.partner_1.ids,
                    subject='This should not be accepted',
                    **parameters
                )

        # support of subtype xml id
        new_message = test_record.message_notify(
            body=Markup('<p>You will not receive a notification</p>'),
            partner_ids=self.partner_1.ids,
            subtype_xmlid='mail.mt_note',
        )
        self.assertEqual(new_message.subtype_id, self.env.ref('mail.mt_note'))

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_notify_thread(self):
        """ Test notify on ``mail.thread`` model, which is pushing a message to
        people without having a document. """
        with self.mock_mail_gateway():
            new_notification = self.env['mail.thread'].message_notify(
                body=Markup('<p>You have received a notification</p>'),
                partner_ids=[self.partner_1.id, self.partner_admin.id, self.partner_employee_2.id],
                subject='This should be a subject',
            )

        self.assertMailNotifications(
            new_notification,
            [{
                'content': '<p>You have received a notification</p>',
                'message_type': 'user_notification',
                'message_values': {
                    'author_id': self.partner_employee,
                    'body': '<p>You have received a notification</p>',
                    'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                    'model': False,
                    'res_id': False,
                    'notified_partner_ids': self.partner_1 | self.partner_employee_2 | self.partner_admin,
                    'subtype_id': self.env.ref('mail.mt_note'),
                },
                'notif': [
                    {'partner': self.partner_1, 'type': 'email',},
                    {'partner': self.partner_employee_2, 'type': 'email',},
                    {'partner': self.partner_admin, 'type': 'email',},
                ],
                'subtype': 'mail.mt_note',
            }],
        )


@tagged('mail_post')
class TestMessageLog(TestMessagePostCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessageLog, cls).setUpClass()
        # ensure employee can create partners, necessary for templates
        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls.test_records, cls.test_partners = cls._create_records_for_batch(
            'mail.test.ticket',
            10,
        )

    @users('employee')
    def test_message_log(self):
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)
        test_record.message_subscribe(self.partner_employee_2.ids)

        with self.mock_mail_gateway():
            new_note = test_record._message_log(
                body=Markup('<p>Labrador</p>'),
            )
        self.assertMailNotifications(
            new_note,
            [{
                'content': '<p>Labrador</p>',
                'message_type': 'notification',
                'message_values': {
                    'author_id': self.partner_employee,
                    'body': '<p>Labrador</p>',
                    'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                    'is_internal': True,
                    'model': test_record._name,
                    'notified_partner_ids': self.env['res.partner'],
                    'partner_ids': self.env['res.partner'],
                    'reply_to': formataddr((self.company_admin.name, f'{self.alias_catchall}@{self.alias_domain}')),
                    'res_id': test_record.id,
                },
                'notif': [],
                'subtype': 'mail.mt_note',
            }],
        )

    @users('employee')
    def test_message_log_batch(self):
        test_records = self.test_records.with_env(self.env)
        test_records.message_subscribe(self.partner_employee_2.ids)

        with self.mock_mail_gateway():
            new_notes = test_records._message_log_batch(
                bodies={
                    test_record.id: Markup('<p>Test _message_log_batch</p>')
                    for test_record in test_records
                },
            )
        for test_record, new_note in zip(test_records, new_notes):
            self.assertMailNotifications(
                new_note,
                [{
                    'content': '<p>Test _message_log_batch</p>',
                    'message_type': 'notification',
                    'message_values': {
                        'author_id': self.partner_employee,
                        'body': '<p>Test _message_log_batch</p>',
                        'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                        'is_internal': True,
                        'model': test_record._name,
                        'notified_partner_ids': self.env['res.partner'],
                        'partner_ids': self.env['res.partner'],
                        'reply_to': formataddr((self.company_admin.name, f'{self.alias_catchall}@{self.alias_domain}')),
                        'res_id': test_record.id,
                    },
                    'notif': [],
                    'subtype': 'mail.mt_note',
                }],
            )

    @users('employee')
    def test_message_log_batch_with_partners(self):
        """ Partners can be given to log, but this should not generate any
        notification. """
        test_records = self.test_records.with_env(self.env)
        test_records.message_subscribe(self.partner_employee_2.ids)

        with self.mock_mail_gateway():
            new_notes = test_records._message_log_batch(
                bodies={
                    test_record.id: Markup('<p>Test _message_log_batch</p>')
                    for test_record in test_records
                },
                partner_ids=self.test_partners[:5].ids,
            )
        for test_record, new_note in zip(test_records, new_notes):
            self.assertMailNotifications(
                new_note,
                [{
                    'content': '<p>Test _message_log_batch</p>',
                    'message_type': 'notification',
                    'message_values': {
                        'author_id': self.partner_employee,
                        'body': '<p>Test _message_log_batch</p>',
                        'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                        'is_internal': True,
                        'model': test_record._name,
                        'notified_partner_ids': self.env['res.partner'],
                        'partner_ids': self.test_partners[:5],
                        'reply_to': formataddr((self.company_admin.name, f'{self.alias_catchall}@{self.alias_domain}')),
                        'res_id': test_record.id,
                    },
                    'notif': [],
                    'subtype': 'mail.mt_note',
                }],
            )

    @users('employee')
    def test_message_log_with_view(self):
        test_records = self.test_records.with_env(self.env)
        test_records.message_subscribe(self.partner_employee_2.ids)

        with self.mock_mail_gateway():
            new_notes = test_records._message_log_with_view(
                'test_mail.mail_template_simple_test',
                render_values={'partner': self.user_employee.partner_id}
            )
        for test_record, new_note in zip(test_records, new_notes):
            self.assertMailNotifications(
                new_note,
                [{
                    'content': f'<p>Hello {self.user_employee.name}, this comes from {test_record.name}.</p>',
                    'message_type': 'notification',
                    'message_values': {
                        'author_id': self.partner_employee,
                        'body': f'<p>Hello {self.user_employee.name}, this comes from {test_record.name}.</p>',
                        'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                        'is_internal': True,
                        'model': test_record._name,
                        'notified_partner_ids': self.env['res.partner'],
                        'reply_to': formataddr((self.company_admin.name, f'{self.alias_catchall}@{self.alias_domain}')),
                        'res_id': test_record.id,
                    },
                    'notif': [],
                    'subtype': 'mail.mt_note',
                }],
            )


@tagged('mail_post')
class TestMessagePost(TestMessagePostCommon, CronMixinCase):

    def test_assert_initial_values(self):
        """ Be sure of what we are testing """
        self.assertFalse(self.test_record.message_ids)
        self.assertFalse(self.test_record.message_follower_ids)
        self.assertFalse(self.test_record.message_partner_ids)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_manual_send_user_notification_email_from_queue(self):
        """ Test sending a mail from the queue that is not related to the admin user sending it.
        Will throw a security error not having access to the mail."""

        with self.mock_mail_gateway():
            new_notification = self.test_record.message_notify(
                subject='This should be a subject',
                body='<p>You have received a notification</p>',
                partner_ids=[self.partner_1.id],
                subtype_xmlid='mail.mt_note',
                force_send=False
            )

        self.assertNotIn(self.user_admin.partner_id, new_notification.mail_ids.partner_ids, "Our admin user should not be within the partner_ids")

        with self.mock_mail_gateway():
            new_notification.mail_ids.with_user(self.user_admin).send()

        self.assertEqual(new_notification.mail_ids.state, 'exception', 'Email will be sent but with exception state - write access denied')

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    def test_message_post(self):
        self.user_employee_2.write({'notification_type': 'inbox'})
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)

        with self.assertSinglePostNotifications(
                [{'partner': self.partner_employee_2, 'type': 'inbox'}],
                message_info={
                    'content': 'Body',
                    'message_values': {
                        'author_id': self.partner_employee,
                        'body': '<p>Body</p>',
                        'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                        'is_internal': False,
                        'message_type': 'comment',
                        'model': test_record._name,
                        'notified_partner_ids': self.partner_employee_2,
                        'reply_to': formataddr((f'{self.company_admin.name} {test_record.name}', f'{self.alias_catchall}@{self.alias_domain}')),
                        'res_id': test_record.id,
                        'subtype_id': self.env.ref('mail.mt_comment'),
                    },
                }
            ):
            new_message = test_record.message_post(
                body='Body',
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                partner_ids=[self.partner_employee_2.id],
            )
        self.assertEqual(test_record.message_partner_ids, self.partner_employee)

        # subscribe partner_1, check notifications
        test_record.message_subscribe(self.partner_1.ids)
        with self.assertSinglePostNotifications(
                [{'partner': self.partner_employee_2, 'type': 'inbox'},
                 {'partner': self.partner_1, 'type': 'email'}],
                message_info={
                    'content': 'NewBody',
                    'email_values': {
                        'headers': {
                            'Return-Path': f'{self.alias_bounce}@{self.alias_domain}',
                        },
                    },
                    'message_values': {
                        'notified_partner_ids': self.partner_1 + self.partner_employee_2,
                    },
                },
                mail_unlink_sent=True
            ):
            new_message = test_record.message_post(
                body='NewBody',
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                partner_ids=[self.partner_employee_2.id],
            )

        # notifications emails should have been deleted
        self.assertFalse(self.env['mail.mail'].sudo().search_count([('mail_message_id', '=', new_message.id)]))

        with self.assertSinglePostNotifications(
                [{'partner': self.partner_1, 'type': 'email'},
                 {'partner': self.partner_portal, 'type': 'email'}],
                message_info={
                    'content': 'ToPortal',
                }
            ):
            test_record.message_post(
                body='ToPortal',
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                partner_ids=self.partner_portal.ids,
            )

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    @users('employee')
    def test_message_post_author(self):
        """ Test author recognition """
        test_record = self.test_record.with_env(self.env)

        # when a user spoofs the author: the actual author is the current user
        # and not the message author
        with self.assertSinglePostNotifications(
                [{'partner': self.partner_admin, 'type': 'email'}],
                message_info={
                    'content': 'Body',
                    'mail_mail_values': {
                        'author_id': self.partner_employee_2,
                        'email_from': formataddr((self.partner_employee_2.name, self.partner_employee_2.email_normalized)),
                    },
                    'message_values': {
                        'author_id': self.partner_employee_2,
                        'email_from': formataddr((self.partner_employee_2.name, self.partner_employee_2.email_normalized)),
                        'message_type': 'comment',
                        'notified_partner_ids': self.partner_admin,
                        'subtype_id': self.env.ref('mail.mt_comment'),
                    },
                },
            ):
            _new_message = test_record.message_post(
                author_id=self.partner_employee_2.id,
                body='Body',
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                partner_ids=[self.partner_admin.id],
            )
        self.assertEqual(test_record.message_partner_ids, self.partner_employee,
                         'Real author is added in followers, not message author')

        # should be skipped with notifications
        test_record.message_unsubscribe(partner_ids=self.partner_employee.ids)
        _new_message = test_record.message_post(
            author_id=self.partner_employee_2.id,
            body='Body',
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            partner_ids=[self.partner_admin.id],
        )
        self.assertFalse(test_record.message_partner_ids, 'Notification should not add author in followers')

        # inactive users are not considered as authors
        self.env.user.with_user(self.user_admin).active = False
        _new_message = test_record.message_post(
            author_id=self.partner_employee_2.id,
            body='Body',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            partner_ids=[self.partner_admin.id],
        )
        self.assertEqual(test_record.message_partner_ids, self.partner_employee_2,
                         'Author is the message author when user is inactive, and shoud be added in followers')

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    @users('employee')
    def test_message_post_defaults(self):
        """ Test default values when posting a classic message. """
        _original_compute_subject = MailTestSimple._message_compute_subject
        _original_notify_headers = MailTestSimple._notify_by_email_get_headers
        _original_notify_mailvals = MailTestSimple._notify_by_email_get_final_mail_values
        test_record = self.env['mail.test.simple'].create([{'name': 'Defaults'}])
        creation_msg = test_record.message_ids
        self.assertEqual(len(creation_msg), 1)

        with patch.object(MailTestSimple, '_message_compute_subject',
                          autospec=True, side_effect=_original_compute_subject) as mock_compute_subject, \
             patch.object(MailTestSimple, '_notify_by_email_get_headers',
                          autospec=True, side_effect=_original_notify_headers) as mock_notify_headers, \
             patch.object(MailTestSimple, '_notify_by_email_get_final_mail_values',
                          autospec=True, side_effect=_original_notify_mailvals) as mock_notify_mailvals, \
             self.mock_mail_gateway(), self.mock_mail_app():
            new_message = test_record.message_post(
                body='Body',
                partner_ids=[self.partner_employee_2.id],
            )

        self.assertEqual(mock_compute_subject.call_count, 1,
                         'Should call model-based subject computation for outgoing emails')
        self.assertEqual(mock_notify_headers.call_count, 1,
                         'Should call model-based headers computation for outgoing emails')
        self.assertEqual(mock_notify_mailvals.call_count, 1,
                         'Should call model-based headers computation for outgoing emails')
        self.assertMailNotifications(
            new_message,
            [{
                'content': '<p>Body</p>',
                'message_type': 'notification',
                'message_values': {
                    'author_id': self.partner_employee,
                    'body': '<p>Body</p>',
                    'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                    'is_internal': False,
                    'model': test_record._name,
                    'notified_partner_ids': self.partner_employee_2,
                    'parent_id': creation_msg,
                    'record_name': test_record.name,
                    'reply_to': formataddr((f'{self.company_admin.name} {test_record.name}', f'{self.alias_catchall}@{self.alias_domain}')),
                    'res_id': test_record.id,
                    'subject': test_record.name,
                },
                'notif': [
                    {'partner': self.partner_employee_2, 'type': 'email',},
                ],
                'subtype': 'mail.mt_note',
            }],
        )

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_message_post_inactive_follower(self):
        """ Test posting with inactive followers does not notify them (e.g. odoobot) """
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)
        test_record._message_subscribe(self.user_employee_2.partner_id.ids)
        self.user_employee_2.write({'active': False})
        self.partner_employee_2.write({'active': False})

        with self.assertPostNotifications([{'content': 'Test', 'notif': []}]):
            test_record.message_post(
                body='Test',
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_message_post_keep_emails(self):
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)
        test_record.message_subscribe(partner_ids=self.partner_employee_2.ids)

        with self.mock_mail_gateway(mail_unlink_sent=True):
            msg = test_record.message_post(
                body='Test',
                mail_auto_delete=False,
                message_type='comment',
                partner_ids=[self.partner_1.id, self.partner_2.id],
                subject='Test',
                subtype_xmlid='mail.mt_comment',
            )

        # notifications emails should not have been deleted: one for customers, one for user
        self.assertEqual(self.env['mail.mail'].sudo().search_count([('mail_message_id', '=', msg.id)]), 2)


    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('erp_manager')
    def test_message_post_mc(self):
        """ Test posting in multi-company environment, notably with aliases """
        records = self.env['mail.test.ticket.mc'].create([
            {
                'name': 'No Specific Company',
            }, {
                'company_id': self.company_admin.id,
                'name': 'Company1',
            }, {
                'company_id': self.company_2.id,
                'name': 'Company2',
            },
        ])
        expected_companies = [self.company_2, self.company_admin, self.company_2]
        expected_alias_domains = [self.mail_alias_domain_c2, self.mail_alias_domain, self.mail_alias_domain_c2]
        for record, expected_company, expected_alias_domain in zip(
            records, expected_companies, expected_alias_domains
        ):
            with self.subTest(record=record):
                with self.assertSinglePostNotifications(
                        [{'partner': self.partner_employee_2, 'type': 'email'}],
                        message_info={
                            'content': 'Body',
                            'email_values': {
                                'headers': {
                                    'Return-Path': f'{expected_alias_domain.bounce_alias}@{expected_alias_domain.name}',
                                },
                            },
                            'mail_mail_values': {
                                'headers': {
                                    'Return-Path': f'{expected_alias_domain.bounce_alias}@{expected_alias_domain.name}',
                                    'X-Odoo-Objects': f'{record._name}-{record.id}',
                                },
                            },
                            'message_values': {
                                'author_id': self.user_erp_manager.partner_id,
                                'email_from': formataddr((self.user_erp_manager.name, self.user_erp_manager.email_normalized)),
                                'is_internal': False,
                                'notified_partner_ids': self.partner_employee_2,
                                'reply_to': formataddr(
                                    (
                                        f'{expected_company.name} {record.name}',
                                        f'{expected_alias_domain.catchall_alias}@{expected_alias_domain.name}'
                                    )
                                ),
                            },
                        }
                    ):
                    _new_message = record.message_post(
                        body='Body',
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                        partner_ids=[self.partner_employee_2.id],
                    )

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_message_post_recipients_email_field(self):
        """ Test various combinations of corner case / not standard filling of
        email fields: multi email, formatted emails, ... """
        partner_emails = [
            'valid.lelitre@agrolait.com, valid.lelitre.cc@agrolait.com',  # multi email
            '"Valid Lelitre" <valid.lelitre@agrolait.com>',  # email contains formatted email
            'wrong',  # wrong
            False, '', ' ',  # falsy
        ]
        expected_tos = [
            # Sends multi-emails
            [f'"{self.partner_1.name}" <valid.lelitre@agrolait.com>',
             f'"{self.partner_1.name}" <valid.lelitre.cc@agrolait.com>',],
            # Avoid double encapsulation
            [f'"{self.partner_1.name}" <valid.lelitre@agrolait.com>',],
            # sent "normally": formats email based on wrong / falsy email
            [f'"{self.partner_1.name}" <@wrong>',],
            [f'"{self.partner_1.name}" <@False>',],
            [f'"{self.partner_1.name}" <@False>',],
            [f'"{self.partner_1.name}" <@ >',],
        ]

        for partner_email, expected_to in zip(partner_emails, expected_tos):
            with self.subTest(partner_email=partner_email, expected_to=expected_to):
                self.partner_1.write({'email': partner_email})
                with self.mock_mail_gateway():
                    self.test_record.with_user(self.user_employee).message_post(
                        body='Test multi email',
                        message_type='comment',
                        partner_ids=[self.partner_1.id],
                        subject='Exotic email',
                        subtype_xmlid='mt_comment',
                    )

                self.assertSentEmail(
                    self.user_employee.partner_id,
                    [self.partner_1],
                    email_to=expected_to,
                )

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_message_schedule', 'odoo.models.unlink')
    def test_message_post_schedule(self):
        """ Test delaying notifications through scheduled_date usage """
        cron_id = self.env.ref('mail.ir_cron_send_scheduled_message').id
        now = datetime.utcnow().replace(second=0, microsecond=0)
        scheduled_datetime = now + timedelta(days=5)
        self.user_admin.write({'notification_type': 'inbox'})

        test_record = self.test_record.with_env(self.env)
        test_record.message_subscribe((self.partner_1 | self.partner_admin).ids)

        with self.mock_datetime_and_now(now), \
             self.assertMsgWithoutNotifications(), \
             self.capture_triggers(cron_id) as capt:
            msg = test_record.message_post(
                body=Markup('<p>Test</p>'),
                message_type='comment',
                subject='Subject',
                subtype_xmlid='mail.mt_comment',
                scheduled_date=scheduled_datetime,
            )
        self.assertEqual(capt.records.call_at, scheduled_datetime,
                         msg='Should have created a cron trigger for the scheduled sending')
        self.assertFalse(self._new_mails)
        self.assertFalse(self._mails)

        schedules = self.env['mail.message.schedule'].sudo().search([('mail_message_id', '=', msg.id)])
        self.assertEqual(len(schedules), 1, msg='Should have scheduled the message')
        self.assertEqual(schedules.scheduled_datetime, scheduled_datetime)

        # trigger cron now -> should not sent as in future
        with self.mock_datetime_and_now(now):
            self.env['mail.message.schedule'].sudo()._send_notifications_cron()
        self.assertTrue(schedules.exists(), msg='Should not have sent the message')

        # Send the scheduled message from the cron at right date
        with self.mock_datetime_and_now(now + timedelta(days=5)), self.mock_mail_gateway(mail_unlink_sent=True):
            self.env['mail.message.schedule'].sudo()._send_notifications_cron()
        self.assertFalse(schedules.exists(), msg='Should have sent the message')
        # check notifications have been sent
        recipients_info = [{'content': '<p>Test</p>', 'notif': [
            {'partner': self.partner_admin, 'type': 'inbox'},
            {'partner': self.partner_1, 'type': 'email'},
        ]}]
        self.assertMailNotifications(msg, recipients_info)

        # manually create a new schedule date, resend it -> should not crash (aka
        # don't create duplicate notifications, ...)
        self.env['mail.message.schedule'].sudo().create({
            'mail_message_id': msg.id,
            'scheduled_datetime': scheduled_datetime,
        })

        # Send the scheduled message from the CRON
        with self.mock_datetime_and_now(now + timedelta(days=5)), self.assertNoNotifications():
            self.env['mail.message.schedule'].sudo()._send_notifications_cron()

        # schedule in the past = send when posting
        with self.mock_datetime_and_now(now), \
             self.mock_mail_gateway(mail_unlink_sent=False), \
             self.capture_triggers(cron_id) as capt:
            msg = test_record.message_post(
                body=Markup('<p>Test</p>'),
                message_type='comment',
                subject='Subject',
                subtype_xmlid='mail.mt_comment',
                scheduled_date=now,
            )
        self.assertFalse(capt.records)
        recipients_info = [{'content': '<p>Test</p>', 'notif': [
            {'partner': self.partner_admin, 'type': 'inbox'},
            {'partner': self.partner_1, 'type': 'email'},
        ]}]
        self.assertMailNotifications(msg, recipients_info)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_message_schedule', 'odoo.models.unlink')
    def test_message_post_schedule_update(self):
        """ Test tools to update scheduled notifications """
        cron = self.env.ref('mail.ir_cron_send_scheduled_message')
        now = datetime.utcnow().replace(second=0, microsecond=0)
        scheduled_datetime = now + timedelta(days=5)
        self.user_admin.write({'notification_type': 'inbox'})

        test_record = self.test_record.with_env(self.env)
        test_record.message_subscribe((self.partner_1 | self.partner_admin).ids)

        with freeze_time(now), \
             self.assertMsgWithoutNotifications():
            msg = test_record.message_post(
                body=Markup('<p>Test</p>'),
                message_type='comment',
                subject='Subject',
                subtype_xmlid='mail.mt_comment',
                scheduled_date=scheduled_datetime,
            )
        schedules = self.env['mail.message.schedule'].sudo().search([('mail_message_id', '=', msg.id)])
        self.assertEqual(len(schedules), 1, msg='Should have scheduled the message')

        # update scheduled datetime, should create new triggers
        with freeze_time(now), \
             self.assertNoNotifications(), \
             self.capture_triggers(cron.id) as capt:
            self.env['mail.message.schedule'].sudo()._update_message_scheduled_datetime(msg, now - timedelta(hours=1))
        self.assertEqual(capt.records.call_at, now - timedelta(hours=1),
                         msg='Should have created a new cron trigger for the new scheduled sending')
        self.assertTrue(schedules.exists(), msg='Should not have sent the message')

        # run cron, notifications have been sent
        with freeze_time(now), self.mock_mail_gateway(mail_unlink_sent=False):
            schedules._send_notifications_cron()
        self.assertFalse(schedules.exists(), msg='Should have sent the message')
        recipients_info = [{'content': '<p>Test</p>', 'notif': [
            {'partner': self.partner_admin, 'type': 'inbox'},
            {'partner': self.partner_1, 'type': 'email'},
        ]}]
        self.assertMailNotifications(msg, recipients_info)

        self.assertFalse(self.env['mail.message.schedule'].sudo()._update_message_scheduled_datetime(msg, now - timedelta(hours=1)),
                         'Mail scheduler: should return False when no schedule is found')

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_message_schedule')
    def test_message_post_w_attachments_filtering(self):
        """
        Test the message_main_attachment heuristics with an emphasis on the XML/Octet/PDF types.
        -> we don't want XML nor Octet-Stream files to be set as message_main_attachment
        """
        xml_attachment, octet_attachment, pdf_attachment = (
            [('List1', b'<xml>My xml attachment</xml>')],
            [('List2', b'\x00\x01My octet-stream attachment\x03\x04')],
            [('List3', b'%PDF My pdf attachment')])

        xml_attachment_data, octet_attachment_data, pdf_attachment_data = self.env['ir.attachment'].create(
            self._generate_attachments_data(3, 'mail.compose.message', 0)
        )
        xml_attachment_data.write({'mimetype': 'application/xml'})
        octet_attachment_data.write({'mimetype': 'application/octet-stream'})
        pdf_attachment_data.write({'mimetype': 'application/pdf'})

        test_record = self.env['mail.test.simple.main.attachment'].with_context(self._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        })
        self.assertFalse(test_record.message_main_attachment_id)

        # test with xml attachment
        with self.mock_mail_gateway():
            test_record.message_post(
                attachments=xml_attachment,
                attachment_ids=xml_attachment_data.ids,
                body='Post XML',
                message_type='comment',
                partner_ids=[self.partner_1.id],
                subject='Test',
                subtype_xmlid='mail.mt_comment',
            )
        self.assertFalse(test_record.message_main_attachment_id,
                         'MailThread: main attachment should not be set with an XML')

        # test with octet attachment
        with self.mock_mail_gateway():
            test_record.message_post(
                attachments=octet_attachment,
                attachment_ids=octet_attachment_data.ids,
                body='Post Octet-Stream',
                message_type='comment',
                partner_ids=[self.partner_1.id],
                subject='Test',
                subtype_xmlid='mail.mt_comment',
            )
        self.assertFalse(test_record.message_main_attachment_id,
                         'MailThread: main attachment should not be set with an Octet-Stream')
        # test with pdf attachment
        with self.mock_mail_gateway():
            test_record.message_post(
                attachments=pdf_attachment,
                attachment_ids=pdf_attachment_data.ids,
                body='Post PDF',
                message_type='comment',
                partner_ids=[self.partner_1.id],
                subject='Test',
                subtype_xmlid='mail.mt_comment',
            )
        self.assertEqual(test_record.message_main_attachment_id, pdf_attachment_data,
                         'MailThread: main attachment should be set to application/pdf')

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_message_schedule')
    def test_message_post_w_attachments_on_main_attachment_model(self):
        """ Test posting a message with attachments on a model inheriting from
        the mixin mail.thread.main.attachment.

        As the mixin inherits from mail.thread, we test mainly features from
        mail.thread but with the ones added of the main attachment mixin.
        """
        _attachments = [
            ('List1', b'My first attachment'),
            ('List2', b'My second attachment'),
        ]
        _attachment_records = self.env['ir.attachment'].create(
            self._generate_attachments_data(3, 'mail.compose.message', 0)
        )
        _attachment_records[1].write({'mimetype': 'image/png'})  # to test message_main_attachment heuristic

        test_record = self.env['mail.test.simple.main.attachment'].with_context(self._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        })
        self._reset_mail_context(test_record)
        self.test_message.model = test_record._name
        self.assertFalse(test_record.message_main_attachment_id)

        with self.mock_mail_gateway():
            msg = test_record.message_post(
                attachments=_attachments,
                attachment_ids=_attachment_records.ids,
                body='Test',
                message_type='comment',
                partner_ids=[self.partner_1.id],
                subject='Test',
                subtype_xmlid='mail.mt_comment',
            )

        # updated message main attachment
        self.assertEqual(test_record.message_main_attachment_id, _attachment_records[1],
                         'MailThread: main attachment should be set to image/png')

        # message attachments
        self.assertEqual(len(msg.attachment_ids), 5)
        self.assertEqual(set(msg.attachment_ids.mapped('res_model')), {test_record._name})
        self.assertEqual(set(msg.attachment_ids.mapped('res_id')), {test_record.id})
        self.assertEqual(set(base64.b64decode(x) for x in msg.attachment_ids.mapped('datas')),
                         set([b'AttContent_00', b'AttContent_01', b'AttContent_02', _attachments[0][1], _attachments[1][1]]))
        self.assertTrue(set(_attachment_records.ids).issubset(msg.attachment_ids.ids),
                        'message_post: mail.message attachments duplicated')

        # notification email attachments
        self.assertEqual(len(self._mails), 1)
        self.assertSentEmail(
            self.user_employee.partner_id, [self.partner_1],
            attachments=[('List1', b'My first attachment', 'text/plain'),
                         ('List2', b'My second attachment', 'text/plain'),
                         ('AttFileName_00.txt', b'AttContent_00', 'text/plain'),
                         ('AttFileName_01.txt', b'AttContent_01', 'image/png'),
                         ('AttFileName_02.txt', b'AttContent_02', 'text/plain'),
                        ]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_multiline_subject(self):
        with self.mock_mail_gateway():
            msg = self.test_record.with_user(self.user_employee).message_post(
                body='<p>Test Body</p>',
                partner_ids=[self.partner_1.id, self.partner_2.id],
                subject='1st line\n2nd line',
            )
        self.assertEqual(msg.subject, '1st line 2nd line')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.mail.models.mail_mail')
    def test_portal_acls(self):
        self.test_record.message_subscribe((self.partner_1 | self.user_employee.partner_id).ids)

        with self.assertPostNotifications(
                [{'content': '<p>Test</p>', 'notif': [
                    {'partner': self.partner_employee, 'type': 'inbox'},
                    {'partner': self.partner_1, 'type': 'email'}]}
                ]
            ), patch.object(MailTestSimple, '_check_access', return_value=None):
            new_msg = self.test_record.with_user(self.user_portal).message_post(
                body=Markup('<p>Test</p>'),
                message_type='comment',
                subject='Subject',
                subtype_xmlid='mail.mt_comment',
            )
        self.assertEqual(new_msg.sudo().notified_partner_ids, (self.partner_1 | self.user_employee.partner_id))

        with self.assertRaises(AccessError):
            self.test_record.with_user(self.user_portal).message_post(
                body=Markup('<p>Test</p>'),
                message_type='comment',
                subject='Subject',
                subtype_xmlid='mail.mt_comment',
            )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_post_answer(self):
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)

        with self.mock_mail_gateway():
            parent_msg = test_record.message_post(
                body=Markup('<p>Test</p>'),
                message_type='comment',
                subject='Test Subject',
                subtype_xmlid='mail.mt_comment',
            )
        self.assertFalse(parent_msg.partner_ids)
        self.assertNotSentEmail()

        # post a first reply
        with self.assertPostNotifications(
                [{'content': '<p>Test Answer</p>', 'notif': [{'partner': self.partner_1, 'type': 'email'}]}]
            ):
            msg = test_record.message_post(
                body=Markup('<p>Test Answer</p>'),
                message_type='comment',
                parent_id=parent_msg.id,
                partner_ids=[self.partner_1.id],
                subject='Welcome',
                subtype_xmlid='mail.mt_comment',
            )
        self.assertEqual(msg.parent_id, parent_msg)
        self.assertEqual(msg.partner_ids, self.partner_1)
        self.assertFalse(parent_msg.partner_ids)

        # check notification emails: references
        self.assertSentEmail(
            self.user_employee.partner_id,
            [self.partner_1],
            # references should be sorted from the oldest to the newest
            references=f'{parent_msg.message_id} {msg.message_id}',
        )

        # post a reply to the reply: check parent is the first one
        with self.mock_mail_gateway():
            new_msg = test_record.message_post(
                body=Markup('<p>Test Answer Bis</p>'),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                parent_id=msg.id,
                partner_ids=[self.partner_2.id],
            )
        self.assertEqual(new_msg.parent_id, parent_msg, 'message_post: flatten error')
        self.assertEqual(new_msg.partner_ids, self.partner_2)
        self.assertSentEmail(
            self.user_employee.partner_id,
            [self.partner_2],
            body_content='<p>Test Answer Bis</p>',
            reply_to=msg.reply_to,
            subject=self.test_record.name,
            references=f'{parent_msg.message_id} {msg.message_id} {new_msg.message_id}',
        )

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_thread')
    @users('employee')
    def test_post_internal(self):
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)

        test_record.message_subscribe([self.user_admin.partner_id.id])
        with self.mock_mail_gateway():
            msg = test_record.message_post(
                body='My Body',
                message_type='comment',
                subject='My Subject',
                subtype_xmlid='mail.mt_note',
            )
        self.assertFalse(msg.is_internal,
                         'Notes are not "internal" but replies will be. Subtype being internal should be sufficient from ACLs point of view.')
        self.assertFalse(msg.partner_ids)
        self.assertFalse(msg.notified_partner_ids)

        self.format_and_process(
            MAIL_TEMPLATE_PLAINTEXT, self.user_admin.email, 'not_my_businesss@example.com',
            msg_id='<1198923581.41972151344608186800.JavaMail.diff1@agrolait.example.com>',
            extra=f'In-Reply-To:\r\n\t{msg.message_id}\n',
            target_model='mail.test.simple')
        reply = test_record.message_ids - msg
        self.assertTrue(reply)
        self.assertTrue(reply.is_internal)
        self.assertEqual(reply.notified_partner_ids, self.user_employee.partner_id)
        self.assertEqual(reply.parent_id, msg)
        self.assertEqual(reply.subtype_id, self.env.ref('mail.mt_note'))


@tagged('mail_post')
class TestMessagePostHelpers(TestMessagePostCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessagePostHelpers, cls).setUpClass()
        # ensure employee can create partners, necessary for templates
        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls.test_records, cls.test_partners = cls._create_records_for_batch(
            'mail.test.ticket',
            10,
        )

        cls._attachments = cls._generate_attachments_data(2, 'mail.template', 0)
        cls.email_1 = 'test1@example.com'
        cls.email_2 = 'test2@example.com'
        cls.test_template = cls._create_template('mail.test.ticket', {
            'attachment_ids': [(0, 0, attach_vals) for attach_vals in cls._attachments],
            'auto_delete': True,
            # After the HTML sanitizer, it will become "<p>Body for: <t t-out="object.name" /><a href="">link</a></p>"
            'body_html': 'Body for: <t t-out="object.name" /><script>test</script><a href="javascript:alert(1)">link</a>',
            'email_cc': cls.partner_1.email,
            'email_to': f'{cls.email_1}, {cls.email_2}',
            'partner_to': '{{ object.customer_id.id }},%s' % cls.partner_2.id,
        })
        cls.test_template.attachment_ids.write({'res_id': cls.test_template.id})
        # Force the attachments of the template to be in the natural order.
        cls.test_template.invalidate_recordset(['attachment_ids'])

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_helpers_source_ref(self):
        """ Test various sources (record or xml id) to ensure source_ref right
        computation. """
        test_records = self.test_records.with_env(self.env)
        template = self.test_template.with_env(self.env)
        view = self.env.ref('test_mail.mail_template_simple_test')

        for source_ref in ('test_mail.mail_test_ticket_tracking_tpl', template,
                           'test_mail.mail_template_simple_test', view):
            with self.subTest(source_ref=source_ref), self.mock_mail_gateway():
                _new_mails = test_records.with_user(self.user_employee).message_mail_with_source(
                    source_ref,
                    render_values={'partner': self.user_employee.partner_id},
                    subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                )

                _new_messages = test_records.with_user(self.user_employee).message_post_with_source(
                    source_ref,
                    render_values={'partner': self.user_employee.partner_id},
                    subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                )

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_mail_with_template(self):
        """ Test sending mass mail on documents based on a template """
        test_records = self.test_records.with_env(self.env)
        template = self.test_template.with_env(self.env)
        with self.mock_mail_gateway():
            _new_mails = test_records.with_user(self.user_employee).message_mail_with_source(
                template,
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
            )

        # created partners from inline email addresses
        new_partners = self.env['res.partner'].search([('email', 'in', (self.email_1, self.email_2))])
        self.assertEqual(len(new_partners), 2,
                         'Post with template: should have created partners based on template emails')

        # sent emails (mass mail mode)
        for test_record in test_records:
            self.assertMailMail(
                new_partners + self.partner_1 + self.partner_2 + test_record.customer_id,
                'sent',
                author=self.user_employee.partner_id,
                email_values={
                    'attachments': [
                        ('AttFileName_00.txt', b'AttContent_00', 'text/plain'),
                        ('AttFileName_01.txt', b'AttContent_01', 'text/plain'),
                    ],
                    'subject': f'About {test_record.name}',
                    'body_content': f'Body for: {test_record.name}',
                },
                fields_values={
                    'auto_delete': True,
                    'is_internal': False,
                    'is_notification': True,  # auto_delete_keep_log -> keep underlying mail.message
                    'message_type': 'email_outgoing',
                    'model': test_record._name,
                    'notified_partner_ids': self.env['res.partner'],
                    'subtype_id': self.env['mail.message.subtype'],
                    'reply_to': formataddr((f'{self.company_admin.name} {test_record.name}', f'{self.alias_catchall}@{self.alias_domain}')),
                    'res_id': test_record.id,
                }
            )

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_mail_with_view(self):
        """ Test sending a mass mailing on documents based on a view """
        test_records = self.test_records.with_env(self.env)
        for test_record in test_records:
            test_record.message_subscribe(test_record.customer_id.ids)

        with self.mock_mail_gateway():
            new_mails = test_records.message_mail_with_source(
                'test_mail.mail_template_simple_test',
                render_values={'partner': self.user_employee.partner_id},
                subject='About mass mailing',
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
            )
        self.assertEqual(len(new_mails), 10)
        self.assertEqual(len(self._new_mails), 10)

        # sent emails (mass mail mode)
        for test_record in test_records:
            self.assertMailMail(
                [test_record.customer_id], 'sent',
                author=self.user_employee.partner_id,
                email_values={
                    'body_content': f'<p>Hello {self.user_employee.partner_id.name}, this comes from {test_record.name}.</p>',
                    'subject': 'About mass mailing',
                },
                fields_values={
                    'auto_delete': False,
                    'is_internal': False,
                    'is_notification': False,  # no to_delete -> no keep_log
                    'message_type': 'email_outgoing',
                    'model': test_record._name,
                    'notified_partner_ids': self.env['res.partner'],
                    'recipient_ids': test_record.customer_id,
                    'subtype_id': self.env['mail.message.subtype'],
                    'reply_to': formataddr((f'{self.company_admin.name} {test_record.name}', f'{self.alias_catchall}@{self.alias_domain}')),
                    'res_id': test_record.id,
                }
            )

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_post_with_source_subtype(self):
        """ Test subtype tweaks when posting with a source """
        test_record = self.test_records.with_env(self.env)[0]
        test_template = self.test_template.with_env(self.env)
        with self.mock_mail_gateway():
            new_message = test_record.with_user(self.user_employee).message_post_with_source(
                test_template,
                subtype_xmlid='mail.mt_activities',
            )
        self.assertEqual(new_message.subtype_id, self.env.ref("mail.mt_activities"))

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_post_with_template(self):
        """ Test posting on a document based on a template content """
        test_record = self.test_records.with_env(self.env)[0]
        test_record.message_subscribe(test_record.customer_id.ids)
        test_template = self.test_template.with_env(self.env)
        with self.mock_mail_gateway():
            new_message = test_record.with_user(self.user_employee).message_post_with_source(
                test_template,
                message_type='comment',
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            )

        # created partners from inline email addresses
        new_partners = self.env['res.partner'].search([('email', 'in', [self.email_1, self.email_2])])
        self.assertEqual(len(new_partners), 2,
                         'Post with template: should have created partners based on template emails')

        # check notifications have been sent
        self.assertMailNotifications(
            new_message,
            [{
                'content': f'<p>Body for: {test_record.name}<a href="">link</a></p>',
                'message_type': 'comment',
                'message_values': {
                    'author_id': self.partner_employee,
                    'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                    'is_internal': False,
                    'model': test_record._name,
                    'reply_to': formataddr((f'{self.company_admin.name} {test_record.name}', f'{self.alias_catchall}@{self.alias_domain}')),
                    'res_id': test_record.id,
                },
                'notif': [
                    {'partner': self.partner_1, 'type': 'email'},
                    {'partner': self.partner_2, 'type': 'email'},
                    {'partner': new_partners[0], 'type': 'email'},
                    {'partner': new_partners[1], 'type': 'email'},
                    {'partner': test_record.customer_id, 'type': 'email'},
                ],
                'subtype': 'mail.mt_comment',
            }]
        )

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_post_with_template_defaults(self):
        """ Test default values, notably subtype being a comment """
        test_record = self.test_records.with_env(self.env)[0]
        test_record.message_subscribe(test_record.customer_id.ids)
        test_template = self.test_template.with_env(self.env)
        with self.mock_mail_gateway():
            new_message = test_record.with_user(self.user_employee).message_post_with_source(
                test_template,
            )

        # created partners from inline email addresses
        new_partners = self.env['res.partner'].search([('email', 'in', [self.email_1, self.email_2])])
        self.assertEqual(len(new_partners), 2,
                         'Post with template: should have created partners based on template emails')

        # check notifications have been sent
        self.assertMailNotifications(new_message, [{
            'content': f'<p>Body for: {test_record.name}<a href="">link</a></p>',
            'message_type': 'notification',
            'message_values': {
                'author_id': self.partner_employee,
                'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                'is_internal': False,
                'model': test_record._name,
                'reply_to': formataddr((f'{self.company_admin.name} {test_record.name}', f'{self.alias_catchall}@{self.alias_domain}')),
                'res_id': test_record.id,
             },
            'notif': [
                {'partner': self.partner_1, 'type': 'email'},
                {'partner': self.partner_2, 'type': 'email'},
                {'partner': new_partners[0], 'type': 'email'},
                {'partner': new_partners[1], 'type': 'email'},
                {'partner': test_record.customer_id, 'type': 'email'},
            ],
            'subtype': 'mail.mt_note',
        }])

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_message_post_with_view(self):
        """ Test posting on documents based on a view """
        test_record = self.test_records.with_env(self.env)[0]
        test_record.message_subscribe(test_record.customer_id.ids)

        with self.mock_mail_gateway():
            new_message = test_record.message_post_with_source(
                'test_mail.mail_template_simple_test',
                message_type='comment',
                render_values={'partner': self.user_employee.partner_id},
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            )

        # check notifications have been sent
        self.assertMailNotifications(new_message, [{
            'content': f'<p>Hello {self.user_employee.partner_id.name}, this comes from {test_record.name}.</p>',
            'message_type': 'comment',
            'message_values': {
                'author_id': self.partner_employee,
                'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                'is_internal': False,
                'message_type': 'comment',
                'model': test_record._name,
                'reply_to': formataddr((f'{self.company_admin.name} {test_record.name}', f'{self.alias_catchall}@{self.alias_domain}')),
                'res_id': test_record.id,
             },
            'notif': [
                {'partner': test_record.customer_id, 'type': 'email'},
            ],
            'subtype': 'mail.mt_comment',
        }])

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_message_post_with_view_defaults(self):
        """ Test posting on documents based on a view, check default values """
        test_record = self.test_records.with_env(self.env)[0]
        test_record.message_subscribe(test_record.customer_id.ids)

        # defaults is a note, take into account specified recipients
        with self.mock_mail_gateway():
            new_message = test_record.message_post_with_source(
                'test_mail.mail_template_simple_test',
                render_values={'partner': self.user_employee.partner_id},
                partner_ids=test_record.customer_id.ids,
            )

        # check notifications have been sent
        self.assertMailNotifications(new_message, [{
            'content': f'<p>Hello {self.user_employee.partner_id.name}, this comes from {test_record.name}.</p>',
            'message_type': 'notification',
            'message_values': {
                'author_id': self.partner_employee,
                'email_from': formataddr((self.partner_employee.name, self.partner_employee.email_normalized)),
                'is_internal': False,
                'message_type': 'notification',
                'model': test_record._name,
                'reply_to': formataddr((f'{self.company_admin.name} {test_record.name}', f'{self.alias_catchall}@{self.alias_domain}')),
                'res_id': test_record.id,
            },
            'notif': [
                {'partner': test_record.customer_id, 'type': 'email'},
            ],
            'subtype': 'mail.mt_note',
        }])


@tagged('mail_post', 'post_install', '-at_install')
class TestMessagePostGlobal(TestMessagePostCommon):

    @users('employee')
    def test_message_post_return(self):
        """ Ensures calling message_post through RPC always return an ID. """
        test_record = self.env['mail.test.simple'].browse(self.test_record.ids)

        # Use call_kw as shortcut to simulate a RPC call.
        message_id = call_kw(self.env['mail.test.simple'],
                             'message_post',
                             [test_record.id],
                             {'body': 'test'})
        self.assertTrue(isinstance(message_id, int))


@tagged('mail_post', 'multi_lang')
class TestMessagePostLang(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMessagePostLang, cls).setUpClass()

        cls.test_records = cls.env['mail.test.lang'].create([
            {'customer_id': False,
             'email_from': 'test.record.1@test.customer.com',
             'lang': 'es_ES',
             'name': 'TestRecord1',
            },
            {'customer_id': cls.partner_2.id,
             'email_from': 'valid.other@gmail.com',
             'name': 'TestRecord2',
            },
        ])

        cls.test_template = cls.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>EnglishBody for <t t-out="object.name"/></p>',
            'email_from': '{{ user.email_formatted }}',
            'email_to': '{{ (object.email_from if not object.customer_id else "") }}',
            'lang': '{{ object.customer_id.lang or object.lang }}',
            'model_id': cls.env['ir.model']._get('mail.test.lang').id,
            'name': 'TestTemplate',
            'partner_to': '{{ object.customer_id.id if object.customer_id else "" }}',
            'subject': 'EnglishSubject for {{ object.name }}',
        })
        cls.user_employee.write({  # add group to create contacts, necessary for templates
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls._activate_multi_lang(test_record=cls.test_records[0], test_template=cls.test_template)

        cls.partner_2.write({'lang': 'es_ES'})

    def test_assert_initial_values(self):
        """ Be sure of what we are testing """
        self.assertEqual(self.partner_1.lang, 'en_US')
        self.assertEqual(self.partner_2.lang, 'es_ES')

        self.assertEqual(self.test_records[0].lang, 'es_ES')
        self.assertEqual(self.test_records[0].customer_id.lang, False)
        self.assertEqual(self.test_records[1].lang, False)
        self.assertEqual(self.test_records[1].customer_id.lang, 'es_ES')

        self.assertFalse(self.test_records[0].message_follower_ids)
        self.assertFalse(self.test_records[1].message_follower_ids)

        self.assertEqual(self.user_employee.lang, 'en_US')

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_lang_template_comment(self):
        """ When posting in comment mode, content is rendered using the lang
        field of template. Notification layout lang is the one from the
        customer to personalize the context. When not found it fallbacks
        on rendered template lang or environment lang. """
        test_record = self.test_records[0].with_user(self.env.user)
        test_template = self.test_template.with_user(self.env.user)

        for partner in self.env['res.partner'] + self.partner_1 + self.partner_2:
            with self.subTest(partner=partner):
                test_record.write({
                    'customer_id': partner.id,
                })
                with self.mock_mail_gateway():
                    test_record.message_post_with_source(
                        test_template,
                        email_layout_xmlid='mail.test_layout',
                        message_type='comment',
                        subtype_id=self.env.ref('mail.mt_comment').id,
                    )

                # expected languages: content depend on template (lang field) aka
                # customer.lang or record.lang (see template); notif lang is
                # partner lang or default DB lang
                exp_content_lang = partner.lang if partner.lang else 'es_ES'
                exp_notif_lang = partner.lang if partner.lang else 'en_US'

                if partner:
                    customer = partner
                else:
                    customer = self.env['res.partner'].search([('email_normalized', '=', 'test.record.1@test.customer.com')], limit=1)
                    self.assertTrue(customer, 'Template usage should have created a contact based on record email')
                self.assertEqual(customer.lang, exp_notif_lang)

                customer_email = self._find_sent_mail_wemail(customer.email_formatted)
                self.assertTrue(customer_email)
                body = customer_email['body']
                # check content: depends on object.lang / object.customer_id.lang
                if exp_content_lang == 'en_US':
                    self.assertIn(f'EnglishBody for {test_record.name}', body,
                                  'Body based on template should be translated')
                else:
                    self.assertIn(f'SpanishBody for {test_record.name}', body,
                                  'Body based on template should be translated')
                # check subject
                if exp_content_lang == 'en_US':
                    self.assertEqual(f'EnglishSubject for {test_record.name}', customer_email['subject'],
                                     'Subject based on template should be translated')
                else:
                    self.assertEqual(f'SpanishSubject for {test_record.name}', customer_email['subject'],
                                     'Subject based on template should be translated')
                # check notification layout content: depends on customer lang
                if exp_notif_lang == 'en_US':
                    self.assertNotIn('Spanish Layout para', body, 'Layout translation failed')
                    self.assertIn('English Layout for Lang Chatter Model', body,
                                  'Layout / model translation failed')
                    self.assertNotIn('Spanish Model Description', body, 'Model translation failed')
                    # check notification layout strings
                    self.assertNotIn('SpanishView Spanish Model Description', body,
                                     '"View document" translation failed')
                    self.assertIn(f'View {test_record._description}', body,
                                  '"View document" translation failed')
                    self.assertNotIn('SpanishButtonTitle', body,
                                     'Groups-based action names translation failed')
                    self.assertIn('NotificationButtonTitle', body,
                                  'Groups-based action names translation failed')
                else:
                    self.assertNotIn('English Layout for', body, 'Layout translation failed')
                    self.assertIn('Spanish Layout para Spanish Model Description', body,
                                  'Layout / model translation failed')
                    self.assertNotIn('Lang Chatter Model', body, 'Model translation failed')
                    # check notification layout strings
                    self.assertIn('SpanishView Spanish Model Description', body,
                                  '"View document" translation failed')
                    self.assertNotIn(f'View {test_record._description}', body,
                                    '"View document" translation failed')
                    self.assertIn('SpanishButtonTitle', body,
                                  'Groups-based action names translation failed')
                    self.assertNotIn('NotificationButtonTitle', body,
                                     'Groups-based action names translation failed')

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_lang_template_mass(self):
        test_records = self.test_records.with_user(self.env.user)
        test_template = self.test_template.with_user(self.env.user)

        with self.mock_mail_gateway():
            test_records.message_mail_with_source(
                test_template,
                email_layout_xmlid='mail.test_layout',
                message_type='comment',
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            )

        record0_customer = self.env['res.partner'].search([('email_normalized', '=', 'test.record.1@test.customer.com')], limit=1)
        self.assertTrue(record0_customer, 'Template usage should have created a contact based on record email')

        for record, customer in zip(test_records, record0_customer + self.partner_2):
            customer_email = self._find_sent_mail_wemail(customer.email_formatted)
            self.assertTrue(customer_email)
            body = customer_email['body']
            # check content
            self.assertIn(f'SpanishBody for {record.name}', body,
                          'Body based on template should be translated')
            # check subject
            self.assertEqual(f'SpanishSubject for {record.name}', customer_email['subject'],
                             'Subject based on template should be translated')

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_layout_email_lang_context(self):
        test_records = self.test_records.with_user(self.env.user).with_context(lang='es_ES')
        test_records[1].message_subscribe(self.partner_2.ids)

        with self.mock_mail_gateway():
            test_records[1].message_post(
                body=Markup('<p>Hello</p>'),
                email_layout_xmlid='mail.test_layout',
                message_type='comment',
                subject='Subject',
                subtype_xmlid='mail.mt_comment',
            )

        customer_email = self._find_sent_mail_wemail(self.partner_2.email_formatted)
        self.assertTrue(customer_email)
        body = customer_email['body']
        # check content
        self.assertIn('<p>Hello</p>', body, 'Body of posted message should be present')
        # check notification layout content
        self.assertIn('Spanish Layout para', body,
                      'Layout content should be translated')
        self.assertNotIn('English Layout for', body)
        self.assertIn('Spanish Layout para Spanish Model Description', body,
                      'Model name should be translated')
        # check notification layout strings
        self.assertIn('SpanishView Spanish Model Description', body,
                      '"View document" should be translated')
        self.assertNotIn(f'View {test_records[1]._description}', body,
                         '"View document" should be translated')
        self.assertIn('SpanishButtonTitle', body, 'Groups-based action names should be translated')
        self.assertNotIn('NotificationButtonTitle', body)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_layout_email_lang_template(self):
        """ Test language support when posting in batch using a template.
        Content is translated based on template definition, layout based on
        customer lang. """
        test_records = self.test_records.with_user(self.env.user)
        test_template = self.test_template.with_user(self.env.user)

        with self.mock_mail_gateway():
            test_records.message_post_with_source(
                test_template,
                email_layout_xmlid='mail.test_layout',
                message_type='comment',
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            )

        record0_customer = self.env['res.partner'].search([('email_normalized', '=', 'test.record.1@test.customer.com')], limit=1)
        self.assertTrue(record0_customer, 'Template usage should have created a contact based on record email')

        for record, customer, exp_notif_lang in zip(
            test_records,
            record0_customer + self.partner_2,
            ('en_US', 'es_ES')  # new customer is en_US, partner_2 is es_ES
        ):
            customer_email = self._find_sent_mail_wemail(customer.email_formatted)
            self.assertTrue(customer_email)

            # body and layouting are translated partly based on template. Bits
            # of layout are not translated due to lang not being correctly
            # propagate everywhere we need it
            body = customer_email['body']
            # check content
            self.assertIn(f'SpanishBody for {record.name}', body,
                          'Body based on template should be translated')
            # check subject
            self.assertEqual(f'SpanishSubject for {record.name}', customer_email['subject'],
                             'Subject based on template should be translated')
            # check notification layout translation
            if exp_notif_lang == 'en_US':
                self.assertNotIn('Spanish Layout para', body,
                                 'Layout content should be translated')
                self.assertIn('English Layout for', body)
                self.assertNotIn('Spanish Layout para Spanish Model Description', body,
                                 'Model name should be translated')
                self.assertNotIn('SpanishView Spanish Model Description', body,
                                 '"View document" should be translated')
                self.assertIn(f'View {test_records[1]._description}', body,
                              '"View document" should be translated')
                self.assertNotIn('SpanishButtonTitle', body,
                                 'Groups-based action names should be translated')
                self.assertIn('NotificationButtonTitle', body,
                              'Groups-based action names should be translated')
            else:
                self.assertIn('Spanish Layout para', body,
                              'Layout content should be translated')
                self.assertNotIn('English Layout for', body)
                self.assertIn('Spanish Layout para Spanish Model Description', body,
                              'Model name should be translated')
                self.assertIn('SpanishView Spanish Model Description', body,
                              '"View document" should be translated')
                self.assertNotIn(f'View {test_records[1]._description}', body,
                                 '"View document" should be translated')
                self.assertIn('SpanishButtonTitle', body,
                              'Groups-based action names should be translated')
                self.assertNotIn('NotificationButtonTitle', body,
                                 'Groups-based action names should be translated')

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_multi_lang_inactive(self):
        """ Test posting using an inactive lang, due do some data in DB. It
        should not crash when trying to search for translated terms / fetch
        lang bits. """
        installed = self.env['res.lang'].get_installed()
        self.assertNotIn('fr_FR', [code for code, _name in installed])
        test_records = self.test_records.with_env(self.env)
        customer_inactive_lang = self.env['res.partner'].create({
            'email': 'test.partner.fr@test.example.com',
            'lang': 'fr_FR',
            'name': 'French Inactive Customer',
        })
        test_records.message_subscribe(partner_ids=customer_inactive_lang.ids)

        for record in test_records:
            with self.subTest(record=record.name):
                with self.mock_mail_gateway(mail_unlink_sent=False), \
                        self.mock_mail_app():
                    record.message_post(
                        body=Markup('<p>Hi there</p>'),
                        email_layout_xmlid='mail.test_layout',
                        message_type='comment',
                        subject='TeDeum',
                        subtype_xmlid='mail.mt_comment',
                    )
                    message = record.message_ids[0]
                    self.assertEqual(message.notified_partner_ids, customer_inactive_lang)

                    email = self._find_sent_email(
                        self.partner_employee.email_formatted,
                        [customer_inactive_lang.email_formatted]
                    )
                    self.assertTrue(bool(email), 'Email not found, check recipients')

                    exp_layout_content_en = 'English Layout for Lang Chatter Model'
                    exp_button_en = 'View Lang Chatter Model'
                    exp_action_en = 'NotificationButtonTitle'
                    self.assertIn(exp_layout_content_en, email['body'])
                    self.assertIn(exp_button_en, email['body'])
                    self.assertIn(exp_action_en, email['body'])

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_multi_lang_recipients(self):
        """ Test posting on a document in a multilang environment. Currently
        current user's lang determines completely language used for notification
        layout notably, when no template is involved.

        Lang layout for this test (to better check various configuration and
        check which lang wins the final output, if any)

          * current users: various between en and es;
          * partner1: es
          * partner2: en
        """
        test_records = self.test_records.with_env(self.env)
        test_records.message_subscribe(partner_ids=(self.partner_1 + self.partner_2).ids)

        for employee_lang, email_layout_xmlid in product(
            ('en_US', 'es_ES'),
            (False, 'mail.test_layout'),
        ):
            with self.subTest(employee_lang=employee_lang, email_layout_xmlid=email_layout_xmlid):
                self.user_employee.write({
                    'lang': employee_lang,
                })
                for record in test_records:
                    with self.mock_mail_gateway(mail_unlink_sent=False), \
                         self.mock_mail_app():
                        record.message_post(
                            body=Markup('<p>Hi there</p>'),
                            email_layout_xmlid=email_layout_xmlid,
                            message_type='comment',
                            subject='TeDeum',
                            subtype_xmlid='mail.mt_comment',
                        )
                        message = record.message_ids[0]
                        self.assertEqual(
                            message.notified_partner_ids, self.partner_1 + self.partner_2
                        )

                        # check created mail.mail and outgoing emails. One email
                        # is generated for each partner 'partner_1' and 'partner_2'
                        # different language thus different layout
                        for partner in self.partner_1 + self.partner_2:
                            _mail = self.assertMailMail(
                                partner, 'sent',
                                mail_message=message,
                                author=self.partner_employee,
                                email_values={
                                    'body_content': '<p>Hi there</p>',
                                    'email_from': self.partner_employee.email_formatted,
                                    'subject': 'TeDeum',
                                },
                            )

                        # Low-level checks on outgoing email for the recipient to
                        # check layouting and language. Note that standard layout
                        # is not tested against translations, only the custom one
                        # to ease translations checks.
                        for partner, exp_lang in zip(
                            self.partner_1 + self.partner_2,
                            ('en_US', 'es_ES')
                        ):
                            email = self._find_sent_email(
                                self.partner_employee.email_formatted,
                                [partner.email_formatted]
                            )
                            self.assertTrue(bool(email), 'Email not found, check recipients')
                            self.assertEqual(partner.lang, exp_lang, 'Test misconfiguration')

                            exp_layout_content_en = 'English Layout for Lang Chatter Model'
                            exp_layout_content_es = 'Spanish Layout para Spanish Model Description'
                            exp_button_en = 'View Lang Chatter Model'
                            exp_button_es = 'SpanishView Spanish Model Description'
                            exp_action_en = 'NotificationButtonTitle'
                            exp_action_es = 'SpanishButtonTitle'
                            if email_layout_xmlid:
                                if exp_lang == 'es_ES':
                                    self.assertIn(exp_layout_content_es, email['body'])
                                    self.assertIn(exp_button_es, email['body'])
                                    self.assertIn(exp_action_es, email['body'])
                                else:
                                    self.assertIn(exp_layout_content_en, email['body'])
                                    self.assertIn(exp_button_en, email['body'])
                                    self.assertIn(exp_action_en, email['body'])
                            else:
                                # check default layouting applies
                                if exp_lang == 'es_ES':
                                    self.assertIn('html lang="es_ES"', email['body'])
                                else:
                                    self.assertIn('html lang="en_US"', email['body'])
