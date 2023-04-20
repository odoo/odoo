# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from unittest.mock import patch
from unittest.mock import DEFAULT

from odoo import exceptions
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.tests.common import tagged, Form, users
from odoo.tools import mute_logger


@tagged('mail_thread')
class TestAPI(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestAPI, cls).setUpClass()
        cls.ticket_record = cls.env['mail.test.ticket'].with_context(cls._test_context).create({
            'email_from': '"Paulette Vachette" <paulette@test.example.com>',
            'name': 'Test',
            'user_id': cls.user_employee.id,
        })

    @mute_logger('openerp.addons.mail.models.mail_mail')
    @users('employee')
    def test_message_update_content(self):
        """ Test updating message content. """
        ticket_record = self.ticket_record.with_env(self.env)
        attachments = self.env['ir.attachment'].create(
            self._generate_attachments_data(2, 'mail.compose.message', 0)
        )

        # post a note
        message = ticket_record.message_post(
            attachment_ids=attachments.ids,
            body=Markup("<p>Initial Body</p>"),
            message_type="comment",
            partner_ids=self.partner_1.ids,
        )
        self.assertEqual(message.attachment_ids, attachments)
        self.assertEqual(set(message.mapped('attachment_ids.res_id')), set(ticket_record.ids))
        self.assertEqual(set(message.mapped('attachment_ids.res_model')), set([ticket_record._name]))
        self.assertEqual(message.body, "<p>Initial Body</p>")
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_note'))

        # update the content with new attachments
        new_attachments = self.env['ir.attachment'].create(
            self._generate_attachments_data(2, 'mail.compose.message', 0)
        )
        ticket_record._message_update_content(
            message, "<p>New Body</p>",
            attachment_ids=new_attachments.ids
        )
        self.assertEqual(message.attachment_ids, attachments + new_attachments)
        self.assertEqual(set(message.mapped('attachment_ids.res_id')), set(ticket_record.ids))
        self.assertEqual(set(message.mapped('attachment_ids.res_model')), set([ticket_record._name]))
        self.assertEqual(message.body, "<p>New Body</p>")

        # void attachments
        ticket_record._message_update_content(
            message, "<p>Another Body, void attachments</p>",
            attachment_ids=[]
        )
        self.assertFalse(message.attachment_ids)
        self.assertFalse((attachments + new_attachments).exists())
        self.assertEqual(message.body, "<p>Another Body, void attachments</p>")

    @mute_logger('openerp.addons.mail.models.mail_mail')
    @users('employee')
    def test_message_update_content_check(self):
        """ Test cases where updating content should be prevented """
        ticket_record = self.ticket_record.with_env(self.env)

        # cannot edit user comments (subtype)
        message = ticket_record.message_post(
            body="<p>Initial Body</p>",
            message_type="comment",
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        with self.assertRaises(exceptions.UserError):
            ticket_record._message_update_content(
                message, "<p>New Body</p>"
            )

        message.sudo().write({'subtype_id': self.env.ref('mail.mt_note')})
        ticket_record._message_update_content(
            message, "<p>New Body</p>"
        )

        # cannot edit notifications
        for message_type in ['notification', 'user_notification', 'email']:
            message.sudo().write({'message_type': message_type})
            with self.assertRaises(exceptions.UserError):
                ticket_record._message_update_content(
                    message, "<p>New Body</p>"
                )


@tagged('mail_thread')
class TestChatterTweaks(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestChatterTweaks, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

    def test_post_no_subscribe_author(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_no_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[self.partner_1.id, self.partner_2.id])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[self.partner_1.id, self.partner_2.id])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_1 | self.partner_2)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_chatter_context_cleaning(self):
        """ Test default keys are not propagated to message creation as it may
        induce wrong values for some fields, like parent_id. """
        parent = self.env['res.partner'].create({'name': 'Parent'})
        partner = self.env['res.partner'].with_context(default_parent_id=parent.id).create({'name': 'Contact'})
        self.assertFalse(partner.message_ids[-1].parent_id)

    def test_chatter_mail_create_nolog(self):
        """ Test disable of automatic chatter message at create """
        rec = self.env['mail.test.simple'].with_user(self.user_employee).with_context({'mail_create_nolog': True}).create({'name': 'Test'})
        self.flush_tracking()
        self.assertEqual(rec.message_ids, self.env['mail.message'])

        rec = self.env['mail.test.simple'].with_user(self.user_employee).with_context({'mail_create_nolog': False}).create({'name': 'Test'})
        self.flush_tracking()
        self.assertEqual(len(rec.message_ids), 1)

    def test_chatter_mail_notrack(self):
        """ Test disable of automatic value tracking at create and write """
        rec = self.env['mail.test.track'].with_user(self.user_employee).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(len(rec.message_ids), 1,
                         "A creation message without tracking values should have been posted")
        self.assertEqual(len(rec.message_ids.sudo().tracking_value_ids), 0,
                         "A creation message without tracking values should have been posted")

        rec.with_context({'mail_notrack': True}).write({'user_id': self.user_admin.id})
        self.flush_tracking()
        self.assertEqual(len(rec.message_ids), 1,
                         "No new message should have been posted with mail_notrack key")

        rec.with_context({'mail_notrack': False}).write({'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(len(rec.message_ids), 2,
                         "A tracking message should have been posted")
        self.assertEqual(len(rec.message_ids.sudo().mapped('tracking_value_ids')), 1,
                         "New tracking message should have tracking values")

    def test_chatter_tracking_disable(self):
        """ Test disable of all chatter features at create and write """
        rec = self.env['mail.test.track'].with_user(self.user_employee).with_context({'tracking_disable': True}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(rec.sudo().message_ids, self.env['mail.message'])
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.write({'user_id': self.user_admin.id})
        self.flush_tracking()
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.with_context({'tracking_disable': False}).write({'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 1)

        rec = self.env['mail.test.track'].with_user(self.user_employee).with_context({'tracking_disable': False}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(len(rec.sudo().message_ids), 1,
                         "Creation message without tracking values should have been posted")
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 0,
                         "Creation message without tracking values should have been posted")

    def test_cache_invalidation(self):
        """ Test that creating a mail-thread record does not invalidate the whole cache. """
        # make a new record in cache
        record = self.env['res.partner'].new({'name': 'Brave New Partner'})
        self.assertTrue(record.name)

        # creating a mail-thread record should not invalidate the whole cache
        self.env['res.partner'].create({'name': 'Actual Partner'})
        self.assertTrue(record.name)


@tagged('mail_thread')
class TestDiscuss(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestDiscuss, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com'
        })

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_mark_all_as_read(self):
        def _employee_crash(*args, **kwargs):
            """ If employee is test employee, consider they have no access on document """
            recordset = args[0]
            if recordset.env.uid == self.user_employee.id and not recordset.env.su:
                if kwargs.get('raise_exception', True):
                    raise exceptions.AccessError('Hop hop hop Ernest, please step back.')
                return False
            return DEFAULT

        with patch.object(MailTestSimple, 'check_access_rights', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                self.env['mail.test.simple'].with_user(self.user_employee).browse(self.test_record.ids).read(['name'])

            employee_partner = self.env['res.partner'].with_user(self.user_employee).browse(self.partner_employee.ids)

            # mark all as read clear needactions
            msg1 = self.test_record.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[employee_partner.id])
            self._reset_bus()
            with self.assertBus(
                    [(self.cr.dbname, 'res.partner', employee_partner.id)],
                    message_items=[{
                        'type': 'mail.message/mark_as_read',
                        'payload': {
                            'message_ids': [msg1.id],
                            'needaction_inbox_counter': 0,
                        },
                    }]):
                employee_partner.env['mail.message'].mark_all_as_read(domain=[])
            na_count = employee_partner._get_needaction_count()
            self.assertEqual(na_count, 0, "mark all as read should conclude all needactions")

            # mark all as read also clear inaccessible needactions
            msg2 = self.test_record.message_post(body='Zest', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[employee_partner.id])
            needaction_accessible = len(employee_partner.env['mail.message'].search([['needaction', '=', True]]))
            self.assertEqual(needaction_accessible, 1, "a new message to a partner is readable to that partner")

            msg2.sudo().partner_ids = self.env['res.partner']
            employee_partner.env['mail.message'].search([['needaction', '=', True]])
            needaction_length = len(employee_partner.env['mail.message'].search([['needaction', '=', True]]))
            self.assertEqual(needaction_length, 1, "message should still be readable when notified")

            na_count = employee_partner._get_needaction_count()
            self.assertEqual(na_count, 1, "message not accessible is currently still counted")

            self._reset_bus()
            with self.assertBus(
                    [(self.cr.dbname, 'res.partner', employee_partner.id)],
                    message_items=[{
                        'type': 'mail.message/mark_as_read',
                        'payload': {
                            'message_ids': [msg2.id],
                            'needaction_inbox_counter': 0,
                        },
                    }]):
                employee_partner.env['mail.message'].mark_all_as_read(domain=[])
            na_count = employee_partner._get_needaction_count()
            self.assertEqual(na_count, 0, "mark all read should conclude all needactions even inacessible ones")

    def test_set_message_done_user(self):
        with self.assertSinglePostNotifications([{'partner': self.partner_employee, 'type': 'inbox'}], message_info={'content': 'Test'}):
            message = self.test_record.message_post(
                body='Test', message_type='comment', subtype_xmlid='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id])
        message.with_user(self.user_employee).set_message_done()
        self.assertMailNotifications(message, [{'notif': [{'partner': self.partner_employee, 'type': 'inbox', 'is_read': True}]}])
        # TDE TODO: it seems bus notifications could be checked

    def test_set_star(self):
        msg = self.test_record.with_user(self.user_admin).message_post(body='My Body', subject='1')
        msg_emp = self.env['mail.message'].with_user(self.user_employee).browse(msg.id)

        # Admin set as starred
        msg.toggle_message_starred()
        self.assertTrue(msg.starred)

        # Employee set as starred
        msg_emp.toggle_message_starred()
        self.assertTrue(msg_emp.starred)

        # Do: Admin unstars msg
        msg.toggle_message_starred()
        self.assertFalse(msg.starred)
        self.assertTrue(msg_emp.starred)

    def test_inbox_message_fetch_needaction(self):
        user1 = self.env['res.users'].create({'login': 'user1', 'name': 'User 1'})
        user1.notification_type = 'inbox'
        user2 = self.env['res.users'].create({'login': 'user2', 'name': 'User 2'})
        user2.notification_type = 'inbox'
        message1 = self.test_record.with_user(self.user_admin).message_post(body='Message 1', partner_ids=[user1.partner_id.id, user2.partner_id.id])
        message2 = self.test_record.with_user(self.user_admin).message_post(body='Message 2', partner_ids=[user1.partner_id.id, user2.partner_id.id])

        # both notified users should have the 2 messages in Inbox initially
        messages = self.env['mail.message'].with_user(user1)._message_fetch(domain=[['needaction', '=', True]])
        self.assertEqual(len(messages), 2)
        messages = self.env['mail.message'].with_user(user2)._message_fetch(domain=[['needaction', '=', True]])
        self.assertEqual(len(messages), 2)

        # first user is marking one message as done: the other message is still Inbox, while the other user still has the 2 messages in Inbox
        message1.with_user(user1).set_message_done()
        messages = self.env['mail.message'].with_user(user1)._message_fetch(domain=[['needaction', '=', True]])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, message2.id)
        messages = self.env['mail.message'].with_user(user2)._message_fetch(domain=[['needaction', '=', True]])
        self.assertEqual(len(messages), 2)

    def test_notification_has_error_filter(self):
        """Ensure message_has_error filter is only returning threads for which
        the current user is author of a failed message."""
        message = self.test_record.with_user(self.user_admin).message_post(
            body='Test', message_type='comment', subtype_xmlid='mail.mt_comment',
            partner_ids=[self.user_employee.partner_id.id]
        )
        self.assertFalse(message.has_error)

        with self.mock_mail_gateway():
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect

            self.user_admin.notification_type = 'email'
            message2 = self.test_record.with_user(self.user_employee).message_post(
                body='Test', message_type='comment', subtype_xmlid='mail.mt_comment',
                partner_ids=[self.user_admin.partner_id.id]
            )
            self.assertTrue(message2.has_error)
        # employee is author of message which has a failure
        threads_employee = self.test_record.with_user(self.user_employee).search([('message_has_error', '=', True)])
        self.assertEqual(len(threads_employee), 1)
        # admin is also author of a message, but it doesn't have a failure
        # and the failure from employee's message should not be taken into account for admin
        threads_admin = self.test_record.with_user(self.user_admin).search([('message_has_error', '=', True)])
        self.assertEqual(len(threads_admin), 0)

    @users("employee")
    def test_suggested_recipients_default_create_value(self):
        """ Test default creation values returned for suggested recipient. """
        email = 'newpartner@example.com'
        data_from_record_mobile = '+33199001015'
        record = self.env['mail.test.ticket'].create({
            'email_from': email,
            'mobile_number': data_from_record_mobile,
        })
        suggestions = record._message_get_suggested_recipients()[record.id]
        self.assertEqual(
            suggestions,
            [(False, email, None, 'Customer Email', {'mobile': '+33199001015', 'phone': False})]
        )

    @users("employee")
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_suggested_recipients_mail_cc(self):
        """ MailThreadCC mixin adds its own suggested recipients management
        coming from CC (carbon copy) management. """
        record = self.env['mail.test.cc'].create({
            'email_cc': 'cc1@example.com, cc2@example.com, cc3 <cc3@example.com>',
        })
        suggestions = record._message_get_suggested_recipients()[record.id]
        self.assertEqual(
            sorted(suggestions),
            [
                (False, '"cc3" <cc3@example.com>', None, 'CC Email', {}),
                (False, 'cc1@example.com', None, 'CC Email', {}),
                (False, 'cc2@example.com', None, 'CC Email', {}),
            ],
            'cc should be in suggestions'
        )

    @users("employee")
    def test_unlink_notification_message(self):
        channel = self.env['discuss.channel'].create({'name': 'testChannel'})
        notification_msg = channel.with_user(self.user_admin).message_notify(
            body='test',
            partner_ids=[self.partner_2.id],
        )

        with self.assertRaises(exceptions.AccessError):
            notification_msg.with_env(self.env).message_format(['id', 'body', 'date', 'author_id', 'email_from'])

        channel_message = self.env['mail.message'].sudo().search([('model', '=', 'discuss.channel'), ('res_id', 'in', channel.ids)])
        self.assertEqual(len(channel_message), 1, "Test message should have been posted")

        channel.sudo().unlink()
        remaining_message = channel_message.exists()
        self.assertEqual(len(remaining_message), 0, "Test message should have been deleted")


@tagged('mail_thread')
class TestNoThread(MailCommon, TestRecipients):
    """ Specific tests for cross models thread features """

    @users('employee')
    def test_message_format(self):
        """ Test formatting of messages when linked to non-thread models.
        Format could be asked notably if an inbox notification due to a
        'message_notify' happens. """
        test_record = self.env['mail.test.nothread'].create({
            'customer_id': self.partner_1.id,
            'name': 'Not A Thread',
        })
        message = self.env['mail.message'].create({
            'model': test_record._name,
            'record_name': 'Not used in message_format',
            'res_id': test_record.id,
        })
        formatted = message.message_format()[0]
        self.assertEqual(formatted['default_subject'], test_record.name)
        self.assertEqual(formatted['record_name'], test_record.name)

        test_record.write({'name': 'Just Test'})
        formatted = message.message_format()[0]
        self.assertEqual(formatted['default_subject'], 'Just Test')
        self.assertEqual(formatted['record_name'], 'Just Test')

    @users('employee')
    def test_message_notify(self):
        """ Test notifying on non-thread models, using MailThread as an abstract
        class with model and res_id giving the record used for notification.

        Test default subject computation is also tested. """
        test_record = self.env['mail.test.nothread'].create({
            'customer_id': self.partner_1.id,
            'name': 'Not A Thread',
        })

        for subject in ["Test Notify", False]:
            with self.subTest():
                with self.assertPostNotifications([{
                        'content': 'Hello Paulo',
                        'email_values': {
                            'reply_to': self.company_admin.catchall_formatted,
                        },
                        'message_type': 'user_notification',
                        'notif': [{
                            'check_send': True,
                            'is_read': True,
                            'partner': self.partner_2,
                            'status': 'sent',
                            'type': 'email',
                        }],
                        'subtype': 'mail.mt_note',
                    }]):
                    _message = self.env['mail.thread'].message_notify(
                        body='<p>Hello Paulo</p>',
                        model=test_record._name,
                        partner_ids=self.partner_2.ids,
                        res_id=test_record.id,
                        subject=subject,
                    )

    @users('employee')
    def test_message_notify_composer(self):
        """ Test comment mode on composer which triggers a notify when model
        does not inherit from mail thread. """
        test_records, _test_partners = self._create_records_for_batch('mail.test.nothread', 2)

        test_reports = self.env['ir.actions.report'].sudo().create([
            {
                'name': 'Test Report on Mail Test Ticket',
                'model': test_records._name,
                'print_report_name': "'TestReport for %s' % object.name",
                'report_type': 'qweb-pdf',
                'report_name': 'test_mail.mail_test_ticket_test_template',
            }, {
                'name': 'Test Report 2 on Mail Test Ticket',
                'model': test_records._name,
                'print_report_name': "'TestReport2 for %s' % object.name",
                'report_type': 'qweb-pdf',
                'report_name': 'test_mail.mail_test_ticket_test_template_2',
            }
        ])
        test_template = self.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>TemplateBody <t t-esc="object.name"></t></p>',
            'email_from': '{{ (user.email_formatted) }}',
            'email_to': '',
            'mail_server_id': self.mail_server_domain.id,
            'partner_to': '{{ object.customer_id.id if object.customer_id else "" }}',
            'name': 'TestTemplate',
            'model_id': self.env['ir.model']._get(test_records._name).id,
            'reply_to': '{{ ctx.get("custom_reply_to") or "info@test.example.com" }}',
            'report_template_ids': [(6, 0, test_reports.ids)],
            'scheduled_date': '{{ (object.create_date or datetime.datetime(2022, 12, 26, 18, 0, 0)) + datetime.timedelta(days=2) }}',
            'subject': 'TemplateSubject {{ object.name }}',
        })
        attachment_data = self._generate_attachments_data(2, test_template._name, test_template.id)
        test_template.write({'attachment_ids': [(0, 0, a) for a in attachment_data]})

        ctx = {
            'default_composition_mode': 'comment',
            'default_model': test_records._name,
            'default_res_domain': [('id', 'in', test_records.ids)],
            'default_template_id': test_template.id,
        }
        # open a composer and run it in comment mode
        composer_form = Form(self.env['mail.compose.message'].with_context(ctx))
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            _, messages = composer._action_send_mail()

        self.assertEqual(len(messages), 2)
        for record, message in zip(test_records, messages):
            self.assertEqual(
                sorted(message.mapped('attachment_ids.name')),
                sorted(['AttFileName_00.txt', 'AttFileName_01.txt',
                        f'TestReport2 for {record.name}.html',
                        f'TestReport for {record.name}.html'])
            )
        self.assertEqual(len(messages.attachment_ids), 8, 'No attachments should be shared')

    @users('employee')
    def test_message_notify_norecord(self):
        """ Test notifying on no record, just using the abstract model itself. """
        with self.assertPostNotifications([{
                'content': 'Hello Paulo',
                'email_values': {
                    'reply_to': self.company_admin.catchall_formatted,
                    'subject': 'Test Notify',
                },
                'message_type': 'user_notification',
                'notif': [{
                    'check_send': True,
                    'is_read': True,
                    'partner': self.partner_2,
                    'status': 'sent',
                    'type': 'email',
                }],
                'subtype': 'mail.mt_note',
            }]):
            _message = self.env['mail.thread'].message_notify(
                body=Markup('<p>Hello Paulo</p>'),
                partner_ids=self.partner_2.ids,
                subject='Test Notify',
            )
