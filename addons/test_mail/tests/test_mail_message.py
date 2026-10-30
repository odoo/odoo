# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from markupsafe import Markup

from odoo import Command
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged, users, HttpCase
from odoo.tools import is_html_empty, mute_logger, formataddr


@tagged('mail_message', 'mail_controller', 'post_install', '-at_install')
class TestMessageHelpersRobustness(MailCommon, HttpCase):
    """ Test message helpers robustness, currently mainly linked to records
    being removed from DB due to cascading deletion, which let side records
    alive in DB. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            email='eglantine@example.com',
            groups='base.group_user',
            login='employee2',
            notification_type='email',
            name='Eglantine Employee',
        )
        cls.partner_employee_2 = cls.user_employee_2.partner_id

        cls.test_records_simple, _partners = cls._create_records_for_batch(
            'mail.test.simple', 3,
        )

    def setUp(self):
        super().setUp()
        # cleanup db
        self.env['mail.notification'].search([('author_id', '=', self.partner_employee.id)]).unlink()

        # handy shortcut variables
        self.deleted_record = self.test_records_simple[2]

        # generate crashed notifications
        with mute_logger('odoo.addons.mail.models.mail_mail'), self.mock_mail_gateway():
            def _send_email(*args, **kwargs):
                raise MailDeliveryException("Some exception")
            self.send_email_mocked.side_effect = _send_email

            for record in self.test_records_simple.with_user(self.user_employee):
                record.message_post(
                    body="Setup",
                    message_type='comment',
                    partner_ids=self.partner_employee_2.ids,
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )

        # In the mean time, some FK deletes the record where the message is
        # # scheduled, skipping its unlink() override
        self.env.cr.execute(
            f"DELETE FROM {self.test_records_simple._table} WHERE id = %s", (self.deleted_record.id,)
        )
        self.env.invalidate_all()

    def test_assert_initial_values(self):
        notifs_by_employee = self.env['mail.notification'].search([('author_id', '=', self.partner_employee.id)])
        self.assertEqual(
            set(notifs_by_employee.mapped('mail_message_id.res_id')),
            set(self.test_records_simple.ids)
        )
        self.assertEqual(len(notifs_by_employee), 3)
        self.assertTrue(all(notif.notification_status == 'exception' for notif in notifs_by_employee))
        self.assertTrue(all(notif.res_partner_id == self.partner_employee_2 for notif in notifs_by_employee))

    def test_load_message_failures(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        with contextlib.suppress(Exception), mute_logger('odoo.http', 'odoo.sql_db'):  # suppress logged error due to readonly route doing an update
            result = self.make_jsonrpc_request("/mail/store", {"fetch_params": ["failures"]})
        self.assertEqual(sorted(r['thread']['id'] for r in result['mail.message']), sorted(self.test_records_simple[:2].ids))
        self.assertEqual(
            sorted(self.env['mail.notification'].search([('author_id', '=', self.partner_employee.id)]).mapped('mail_message_id.res_id')),
            sorted((self.test_records_simple - self.deleted_record).ids),
            'Should have cleaned notifications linked to unexisting records'
        )

    def test_load_message_failures_use_display_name(self):
        test_record = self.env['mail.test.simple.unnamed'].create({'description': 'Some description'})
        test_record.message_subscribe(partner_ids=self.partner_employee_2.ids)

        self.authenticate(self.user_employee.login, self.user_employee.password)
        msg = test_record.message_post(body='Some body', author_id=self.partner_employee.id)
        # simulate failure
        self.env['mail.notification'].create({
            'author_id': msg.author_id.id,
            'mail_message_id': msg.id,
            'res_partner_id': self.partner_employee_2.id,
            'notification_type': 'email',
            'notification_status': 'exception',
            'failure_type': 'mail_email_invalid',
        })
        with contextlib.suppress(Exception), mute_logger('odoo.http', 'odoo.sql_db'):  # suppress logged error due to readonly route doing an update
            res = self.make_jsonrpc_request("/mail/store", {"fetch_params": ["failures"]})
            self.assertEqual(
                sorted(t["name"] for t in res["mail.thread"]),
                sorted(['Some description'] + (self.test_records_simple - self.deleted_record).mapped('display_name'))
            )

    def test_message_fetch(self):
        # set notifications to unread, so that we can simulate inbox usage
        p2_notifications = self.env['mail.notification'].search([('res_partner_id', '=', self.partner_employee_2.id)])
        p2_notifications.read_date = False
        self.authenticate(self.user_employee_2.login, self.user_employee_2.login)
        data = self.make_jsonrpc_request("/mail/store", {"fetch_params": [["/mail/messaging_menu/mail.message/load_more", {"tab_id": "notification", "filter_ids": ["notification_unread"], "limit": 20}]]})
        self.assertEqual(
            {r["thread"]["id"] for r in data["mail.message"]},
            set(self.test_records_simple.ids),
            "Currently reading message on missing record, crash avoided",
        )
        p2_notifications.with_user(self.user_employee_2).mail_message_id.set_message_done()
        data = self.make_jsonrpc_request("/mail/store", {"fetch_params": [["/mail/messaging_menu/mail.message/load_more", {"tab_id": "notification", "limit": 20}]]})
        self.assertEqual(
            {r["thread"]["id"] for r in data["mail.message"]},
            set(self.test_records_simple.ids),
            "Currently reading message on missing record, crash avoided",
        )

    def test_notify_cancel_by_type(self):
        """ Test canceling notifications, notably when having missing records. """
        self.env.invalidate_all()
        notifs_by_employee = self.env['mail.notification'].search([('author_id', '=', self.partner_employee.id)])

        # do not crash even if removed record
        self.test_records_simple.with_user(self.user_employee).notify_cancel_by_type('email')
        self.env.invalidate_all()

        notifs_by_employee = notifs_by_employee.exists()
        self.assertEqual(len(notifs_by_employee), 3, 'Currently keep notifications for missing records')
        self.assertTrue(all(notif.notification_status == 'canceled' for notif in notifs_by_employee))


@tagged("mail_message", "post_install", "-at_install")
class TestMessageValues(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMessageValues, cls).setUpClass()

        cls.alias_record = cls.env['mail.test.container'].create({
            'name': 'Pigs',
            'alias_name': 'pigs',
            'alias_contact': 'followers',
        })
        cls.Message = cls.env['mail.message'].with_user(cls.user_employee)

    @users('employee')
    def test_empty_message(self):
        """ Test that message is correctly considered as empty (see `_filter_empty()`).
        Message considered as empty if:
            - no body or empty body
            - AND no subtype or no subtype description
            - AND no tracking values
            - AND no attachment

        Check _update_content behavior when voiding messages (cleanup side
        records: stars, notifications).
        """
        self.env = self.env(context={**self.env.context, 'lang': 'en_US'})
        note_subtype = self.env.ref('mail.mt_note')
        _attach_1 = self.env['ir.attachment'].with_user(self.user_employee).create({
            'name': 'Attach1',
            'raw': b'migration test',
            'res_id': 0,
            'res_model': 'mail.compose.message',
        })
        record = self.env['mail.test.track'].create({'name': 'EmptyTesting'})
        self.flush_tracking()
        record.message_subscribe(partner_ids=self.partner_admin.ids, subtype_ids=note_subtype.ids)
        message = record.message_post(
            attachment_ids=_attach_1.ids,
            body='Test',
            message_type='comment',
            subtype_id=note_subtype.id,
        )
        message.write({'bookmarked_partner_ids': [(4, self.partner_admin.id)]})

        # check content
        self.assertEqual(len(message.attachment_ids), 1)
        self.assertMessageFields(message.sudo(), {
            'body': '<p>Test</p>',
            'bookmarked_partner_ids': self.partner_admin,
            'notified_partner_ids': self.partner_admin,
            'tracking_values': [],
        })
        self.assertEqual(len(message.sudo().notification_ids), 1)

        # Reset body case
        record._message_update_content(
            message,
            body=Markup("<p><br /></p>"),
            attachment_ids=message.attachment_ids.ids,
        )
        self.assertTrue(is_html_empty(message.body))
        self.assertFalse(message.sudo()._filter_empty(), 'Still having attachments')

        # Subtype content
        note_subtype.sudo().write({'description': 'Very important discussions'})
        record._message_update_content(message, body="", attachment_ids=[])
        self.assertFalse(message.attachment_ids)
        self.assertEqual(message.notified_partner_ids, self.partner_admin)
        self.assertEqual(message.bookmarked_partner_ids, self.partner_admin)
        self.assertFalse(message.sudo()._filter_empty(), 'Subtype with description')

        # Completely emptied now
        note_subtype.sudo().write({'description': ''})
        self.assertEqual(message.sudo()._filter_empty(), message)
        record._message_update_content(message.sudo(), body="", attachment_ids=[])
        self.assertEqual(message.notified_partner_ids, self.partner_admin)  # message still notified (albeit content is removed)
        self.assertEqual(message.bookmarked_partner_ids, self.partner_admin)  # bookmarked messages stay (albeit content is removed)

        # test tracking values model only (no body content)
        record.write({'user_id': self.user_admin.id})
        self.flush_tracking()
        tracking_message = record.message_ids[0]
        tracking_message.sudo().write({'body': False})
        self.assertFalse(tracking_message.attachment_ids)
        self.assertTrue(is_html_empty(tracking_message.body))
        self.assertFalse(tracking_message.subtype_id.description)
        self.assertFalse(tracking_message._filter_empty(), 'Has tracking values')
        with self.assertRaises(UserError, msg='Tracking values prevent from updating content'):
            record._message_update_content(tracking_message, body="", attachment_ids=[])

        # be sure removing them correcly set it as empty
        tracking_message.sudo().write({'tracking_value_ids': [(5, 0)]})
        self.assertEqual(tracking_message._filter_empty(), tracking_message, 'No tracking values a anymore')

    @mute_logger('odoo.models.unlink')
    def test_mail_message_store_access(self):
        """
        User that doesn't have access to a record should still be able to fetch
        the record_name inside message.
        """
        company_2 = self.add_company('base.test_company', {'name': 'Second Test Company'})
        record1 = self.env['mail.test.multi.company'].create({
            'name': 'Test1',
            'company_id': company_2.id,
        })
        message = record1.message_post(body='', partner_ids=[self.user_employee.partner_id.id])
        # We need to flush and invalidate the ORM cache since the record_name
        # is already cached from the creation.
        self.env.flush_all()
        self.env.invalidate_all()
        store_1 = Store().add(message.with_user(self.user_employee), "_store_message_fields")
        self.assertEqual(store_1._build_result()["mail.message"][0].get("record_name"), "Test1")

        record1.write({"name": "Test2"})
        self.env.flush_all()
        self.env.invalidate_all()
        store_2 = Store().add(message.with_user(self.user_employee), "_store_message_fields")
        self.assertEqual(store_2._build_result()["mail.message"][0].get('record_name'), 'Test2')

        # check model not inheriting from mail.thread -> should not crash
        record_nothread = self.env['mail.test.nothread'].create({'name': 'NoThread'})
        message = self.env['mail.message'].create({
            'model': record_nothread._name,
            'res_id': record_nothread.id,
        })
        formatted = Store().add(message, "_store_message_fields")._build_result()["mail.message"][0]
        self.assertEqual(formatted['record_name'], record_nothread.name)

    def test_message_fetch_search_attachment_name(self):
        """ Searching messages of a thread by attachment name matches the
        attachments linked to the thread or to one of its messages, and not
        the ones linked to another record. """
        record, other_record = self.env["mail.test.simple"].create([{"name": "Searched"}, {"name": "Other"}])
        msg_on_thread, msg_on_message, msg_on_other = (
            record.message_post(body=f"Message {idx}", message_type="comment") for idx in range(3)
        )
        attachments = self.env["ir.attachment"].create([
            {
                "raw": b"hello",
                "name": f"report_{res_model}.pdf",
                "res_id": res_id,
                "res_model": res_model,
            }
            for res_model, res_id in [
                (record._name, record.id),
                (msg_on_message._name, msg_on_message.id),
                (other_record._name, other_record.id),
            ]
        ])
        for message, attachment in zip(msg_on_thread + msg_on_message + msg_on_other, attachments):
            message.attachment_ids = [Command.link(attachment.id)]

        res = self.Message._message_fetch(domain=None, thread=record, search_term="report")
        self.assertEqual(res["messages"], msg_on_thread + msg_on_message)

    def test_records_by_message(self):
        record1 = self.env["mail.test.simple"].create({"name": "Test1"})
        record2 = self.env["mail.test.simple"].create({"name": "Test1"})
        record3 = self.env["mail.test.nothread"].create({"name": "Test2"})
        messages = self.env["mail.message"].create(
            [
                {
                    "model": record._name,
                    "res_id": record.id,
                }
                for record in [record1, record2, record3]
            ]
        )
        # methods called on batch of message
        records_by_model_name = messages._records_by_model_name()
        test_simple_records = records_by_model_name["mail.test.simple"]
        self.assertEqual(test_simple_records, record1 + record2)
        self.assertEqual(test_simple_records._prefetch_ids, tuple((record1 + record2).ids))
        test_no_thread_records = records_by_model_name["mail.test.nothread"]
        self.assertEqual(test_no_thread_records, record3)
        self.assertEqual(test_no_thread_records._prefetch_ids, tuple(record3.ids))
        record_by_message = messages._record_by_message()
        m0_records = record_by_message[messages[0]]
        self.assertEqual(m0_records, record1)
        self.assertEqual(m0_records._prefetch_ids, tuple((record1 + record2).ids))
        m1_records = record_by_message[messages[1]]
        self.assertEqual(m1_records, record2)
        self.assertEqual(m1_records._prefetch_ids, tuple((record1 + record2).ids))
        m2_records = record_by_message[messages[2]]
        self.assertEqual(m2_records, record3)
        self.assertEqual(m2_records._prefetch_ids, tuple(record3.ids))
        # methods called on individual message from a batch: prefetch from batch is kept
        records_by_model_name = messages[0]._records_by_model_name()
        test_simple_records = records_by_model_name["mail.test.simple"]
        self.assertEqual(test_simple_records, record1)
        self.assertEqual(test_simple_records._prefetch_ids, tuple((record1 + record2).ids))
        record_by_message = messages[0]._record_by_message()
        m0_records = record_by_message[messages[0]]
        self.assertEqual(m0_records, record1)
        self.assertEqual(m0_records._prefetch_ids, tuple((record1 + record2).ids))

    def test_mail_message_values_body_base64_image(self):
        msg = self.env['mail.message'].with_user(self.user_employee).create({
            'body': 'taratata <img src="data:image/png;base64,iV/+OkI=" width="2"> <img src="data:image/png;base64,iV/+OkI=" width="2">',
        })
        self.assertEqual(len(msg.attachment_ids), 1)
        attachment = msg.attachment_ids[0]
        self.assertEqual(
            msg.body,
            f'<p>taratata <img src="/web/image/{attachment.id}?access_token={attachment.access_token}" alt="image0" data-attachment-id="{attachment.id}" width="2"> '
            f'<img src="/web/image/{attachment.id}?access_token={attachment.access_token}" alt="image0" data-attachment-id="{attachment.id}" width="2"></p>'
        )

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.models')
    @users('employee')
    def test_mail_message_values_fromto_long_name(self):
        """ Long headers may break in python if above 68 chars for certain
        DKIM verification stacks as folding is not done correctly
        (see ``_notify_get_reply_to_formatted_email`` docstring
        + commit linked to this test). """
        # name would make it blow up: keep only email
        test_record = self.env['mail.test.container'].browse(self.alias_record.ids)
        self.user_employee.write({
            'name': 'Super Long Name That People May Enter "Even with an internal quoting of stuff"'
        })
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        reply_to_email = f"{test_record.alias_name}@{self.alias_domain}"
        self.assertEqual(msg.reply_to, reply_to_email,
                         'Reply-To: use only email when formataddr > 68 chars')

        # whatever the record and company names, email is too long: keep only email
        test_record.write({
            'alias_name': 'Waaaay too long alias name that should make any reply-to blow the 68 characters limit',
            'name': 'Short',
        })
        sanitized_alias_name = 'waaaay-too-long-alias-name-that-should-make-any-reply-to-blow-the-68-characters-limit'
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, f"{sanitized_alias_name}@{self.alias_domain}",
                         'Reply-To: even a long email is ok as only formataddr is problematic')

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_no_document_values(self):
        msg = self.Message.create({
            'reply_to': 'test.reply@example.com',
            'email_from': 'test.from@example.com',
        })
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, 'test.reply@example.com')
        self.assertEqual(msg.email_from, 'test.from@example.com')

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_no_document(self):
        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        reply_to_name = self.user_employee.name
        reply_to_email = '%s@%s' % (self.alias_catchall, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias domain -> author
        self.env.company.sudo().alias_domain_id = False
        self.assertFalse(self.env.company.catchall_email)

        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_document_alias(self):
        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        reply_to_name = self.user_employee.name
        reply_to_email = '%s@%s' % (self.alias_record.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias domain, no company catchall -> author
        self.alias_record.alias_domain_id = False
        self.env.company.sudo().alias_domain_id = False
        self.assertFalse(self.env.company.catchall_email)

        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        self.assertEqual(msg.reply_to, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # alias wins over company, hence no catchall is not an issue
        self.alias_record.alias_domain_id = self.mail_alias_domain

        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_document_no_alias(self):
        test_record = self.env['mail.test.simple'].create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        msg = self.Message.create({
            'model': 'mail.test.simple',
            'res_id': test_record.id
        })
        self.assertIn('-openerp-%d-mail.test.simple' % test_record.id, msg.message_id.split('@')[0])
        reply_to_name = self.user_employee.name
        reply_to_email = '%s@%s' % (self.alias_catchall, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @users('employee')
    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_document_manual_alias(self):
        test_record = self.env['mail.test.simple'].create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        alias = self.env['mail.alias'].sudo().create({
            'alias_name': 'MegaLias',
            'alias_model_id': self.env['ir.model']._get('mail.test.simple').id,
            'alias_parent_model_id': self.env['ir.model']._get('mail.test.simple').id,
            'alias_parent_thread_id': test_record.id,
        })

        msg = self.Message.create({
            'model': 'mail.test.simple',
            'res_id': test_record.id
        })

        self.assertIn('-openerp-%d-mail.test.simple' % test_record.id, msg.message_id.split('@')[0])
        reply_to_name = self.user_employee.name
        reply_to_email = '%s@%s' % (alias.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @users('employee')
    def test_mail_message_values_fromto_reply_to_force_new(self):
        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id,
            'reply_to_force_new': True,
        })
        self.assertIn('reply_to', msg.message_id.split('@')[0])
        self.assertNotIn('mail.test.container', msg.message_id.split('@')[0])
        self.assertNotIn('-%d-' % self.alias_record.id, msg.message_id.split('@')[0])

    def test_mail_message_values_misc(self):
        """ Test various values on mail.message, notably default values """
        msg = self.env['mail.message'].create({'model': self.alias_record._name, 'res_id': self.alias_record.id})
        self.assertEqual(msg.message_type, 'comment', 'Message should be comments by default')

    def test_mail_message_write_invalidate_documents(self):
        """ Writing on messages of several documents invalidates the messages
        cache of all those documents, not only the first one. """
        records = self.env['mail.test.simple'].with_context(self._test_context).create([
            {'name': f'Test {idx}'} for idx in range(3)
        ])
        messages = self.env['mail.message'].create([
            {'body': f'Message {idx}', 'message_type': 'comment', 'model': record._name, 'res_id': record.id}
            for idx, record in enumerate(records[:2])
        ])
        for record, message in zip(records[:2], messages):
            self.assertEqual(record.message_ids, message)

        messages.write({'res_id': records[2].id})
        for record in records[:2]:
            self.assertFalse(record.message_ids)
        self.assertEqual(records[2].message_ids, messages)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_message_write_edited_by(self):
        """ Message posted by an employee, edited by an administrator through
        Manage Messages: the edited tooltip shows the administrator name. When
        the author edits it again from the chatter, the tooltip no longer names
        anybody, as the last editor is the author. """
        employee_partner = self.user_employee.partner_id
        admin_partner = self.user_admin.partner_id
        record = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test'})
        record = record.with_user(self.user_employee)
        message = record.message_post(
            body=Markup("<p>Initial Body</p>"),
            message_type="comment",
        )
        self.assertEqual(message.author_id, employee_partner)
        self.assertFalse(message._get_edited_by_partner())

        # administrator edits the body from Manage Messages (direct write)
        with freeze_time('2025-04-08 10:00:00'):
            message.with_user(self.user_admin).with_context(mail_message_mark_edited=True).write({
                'body': Markup("<p>Edited by admin</p>"),
            })
        self.assertEqual(
            message.body,
            Markup(f'<p>Edited by admin <span class="o-mail-Message-edited" data-o-datetime="2025-04-08 10:00:00" data-o-edited-by="{admin_partner.id}"></span></p>'),
        )
        self.assertEqual(message.author_id, employee_partner, "Editing the body must not change the author")
        store_data = Store().add(message.with_user(self.user_employee), "_store_message_fields")._build_result()
        self.assertEqual(store_data["mail.message"][0]["edited_by_partner_id"], admin_partner.id,
                         "Edited by someone else than the author: tooltip shows the editor name")

        # author edits it again from the chatter
        with freeze_time('2025-04-08 11:00:00'):
            record._message_update_content(message.with_user(self.user_employee), body=Markup("<p>Edited by author</p>"))
        self.assertEqual(
            message.body,
            Markup(f'<p>Edited by author <span class="o-mail-Message-edited" data-o-datetime="2025-04-08 11:00:00" data-o-edited-by="{employee_partner.id}"></span></p>'),
            "Only one edited marker is kept, with the last editor",
        )
        self.assertEqual(message.author_id, employee_partner)
        store_data = Store().add(message.with_user(self.user_employee), "_store_message_fields")._build_result()
        self.assertEqual(store_data["mail.message"][0]["edited_by_partner_id"], employee_partner.id,
                         "Last editor is the author: tooltip does not show a name")

    @mute_logger('odoo.addons.base.models.ir_access')
    def test_mail_message_write_manage_messages(self):
        """ Manage Messages (direct write on mail.message): normal users cannot
        edit messages of others; administrators can edit the body only, never
        the author, the date or the document of the message. """
        self.assertFalse(self.user_employee._is_admin())
        self.assertTrue(self.user_admin._is_admin())
        admin_partner = self.user_admin.partner_id
        record = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test'})
        other_record = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Other'})
        with freeze_time('2025-04-08 09:00:00'):
            message = record.with_user(self.user_admin).message_post(
                body=Markup("<p>Initial Body</p>"),
                message_type="comment",
            )
        initial_values = {
            'author_guest_id': message.author_guest_id,
            'author_id': message.author_id,
            'date': message.date,
            'email_from': message.email_from,
            'model': message.model,
            'res_id': message.res_id,
        }
        self.assertEqual(message.author_id, admin_partner)

        # normal user cannot edit the content of a message written by someone else
        with self.assertRaises(AccessError):
            message.with_user(self.user_employee).write({'body': Markup("<p>Edited by employee</p>")})
        self.assertEqual(message.body, "<p>Initial Body</p>")

        # nobody but superuser can change author, date or document, administrators included
        guest = self.env['mail.guest'].create({'name': 'Guest'})
        for user in (self.user_employee, self.user_admin):
            for fname, value in [
                ('author_id', self.user_employee.partner_id.id),
                ('author_guest_id', guest.id),
                ('email_from', 'hacker@test.example.com'),
                ('date', '2020-01-01 10:00:00'),
                ('model', other_record._name),
                ('res_id', other_record.id),
            ]:
                with self.subTest(user=user.login, fname=fname), self.assertRaises(AccessError):
                    message.with_user(user).write({fname: value})
        # locked fields block the whole write, body included
        with self.assertRaises(AccessError):
            message.with_user(self.user_admin).write({
                'author_id': self.user_employee.partner_id.id,
                'body': Markup("<p>Edited with author</p>"),
            })
        self.assertEqual(message.body, "<p>Initial Body</p>")
        for fname, value in initial_values.items():
            self.assertEqual(message[fname], value, f"{fname} should not have been modified")

        # administrator can edit the body, which is marked as edited
        with freeze_time('2025-04-08 10:00:00'):
            message.with_user(self.user_admin).with_context(mail_message_mark_edited=True).write({
                'body': Markup("<p>Edited by admin</p>"),
            })
        self.assertEqual(
            message.body,
            Markup(f'<p>Edited by admin <span class="o-mail-Message-edited" data-o-datetime="2025-04-08 10:00:00" data-o-edited-by="{admin_partner.id}"></span></p>'),
        )
        for fname, value in initial_values.items():
            self.assertEqual(message[fname], value, f"{fname} should not have been modified")


@tagged("mail_message", "mail_gc")
class TestMailNotification(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()

    def test_gc_notifications(self):
        """ Read notifications of internal users with a final status are removed
        'max_age_days' after being read, by batches. Read dates come from the
        transaction (cr.now), hence the use of mock_datetime_and_now. """
        now = datetime(2025, 6, 1, 10, 0, 0)
        old_dt, recent_dt = now - relativedelta(days=120), now - relativedelta(days=30)
        record = self.env['mail.test.simple'].create({'name': 'Test'})
        notifications = {}
        # (date, mark as done by employee, [(name, partner, type, status)])
        for msg_dt, mark_done, cases in [
            (old_dt, True, [
                ('old_inbox_read', self.partner_employee, 'inbox', 'sent'),
                ('old_email', self.partner_admin, 'email', 'sent'),
                ('old_email_portal', self.partner_portal, 'email', 'sent'),
            ]),
            (old_dt, False, [
                ('old_inbox_unread', self.partner_employee, 'inbox', 'sent'),
                ('old_email_exception', self.partner_admin, 'email', 'exception'),
            ]),
            (recent_dt, True, [
                ('recent_inbox_read', self.partner_employee, 'inbox', 'sent'),
                ('recent_email', self.partner_admin, 'email', 'sent'),
            ]),
        ]:
            with self.mock_datetime_and_now(msg_dt):
                message = self.env['mail.message'].create({
                    'body': 'Test', 'model': record._name, 'res_id': record.id,
                })
                for name, partner, notification_type, status in cases:
                    notifications[name] = self.env['mail.notification'].create({
                        'mail_message_id': message.id,
                        'notification_status': status,
                        'notification_type': notification_type,
                        'res_partner_id': partner.id,
                    })
                if mark_done:
                    message.with_user(self.user_employee).set_message_done()

        # email notifications are read at creation, inbox ones when marked as done
        for name, notification in notifications.items():
            with self.subTest(notification=name):
                if name == 'old_inbox_unread':
                    self.assertFalse(notification.read_date)
                else:
                    self.assertEqual(notification.read_date, recent_dt if name.startswith('recent') else old_dt)

        # not the default 180 days, as nothing would be removed; limit to check batches
        with self.mock_datetime_and_now(now), \
             patch('odoo.addons.mail.models.mail_notification.GC_UNLINK_LIMIT', 1):
            results = [self.env['mail.notification']._gc_notifications(max_age_days=90) for _i in range(3)]
        self.assertEqual(results, [(1, True), (1, True), (0, False)])
        removed = {name for name, notification in notifications.items() if not notification.exists()}
        self.assertEqual(removed, {'old_inbox_read', 'old_email'})
