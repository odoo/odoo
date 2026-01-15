# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib

from markupsafe import Markup

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import UserError
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
            result = self.make_jsonrpc_request("/mail/data", {"failures": True})
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
            res = self.make_jsonrpc_request("/mail/data", {"failures": True})
            self.assertEqual(
                sorted(t["name"] for t in res["mail.thread"]),
                sorted(['Some description'] + (self.test_records_simple - self.deleted_record).mapped('display_name'))
            )

    def test_message_fetch(self):
        # set notifications to unread, so that we can simulate inbox usage
        p2_notifications = self.env['mail.notification'].search([('res_partner_id', '=', self.partner_employee_2.id)])
        p2_notifications.is_read = False

        self.authenticate(self.user_employee_2.login, self.user_employee_2.login)
        result = self.make_jsonrpc_request("/mail/inbox/messages", {})['data']
        self.assertEqual(
            {r['thread']['id'] for r in result['mail.message']}, set(self.test_records_simple.ids),
            'Currently reading message on missing record, crash avoided'
        )
        p2_notifications.with_user(self.user_employee_2).mail_message_id.set_message_done()

        result = self.make_jsonrpc_request("/mail/history/messages", {})['data']
        self.assertEqual(
            {r['thread']['id'] for r in result['mail.message']}, set(self.test_records_simple.ids),
            'Currently reading message on missing record, crash avoided'
        )

    def test_message_link_by_employee(self):
        record = self.test_records_simple[0]
        thread_message = record.message_post(body='Thread Message', message_type='comment')
        deleted_message = record.message_post(body='', message_type='comment')
        self.authenticate(self.user_employee.login, self.user_employee.login)
        with self.subTest(thread_message=thread_message):
            expected_url = self.base_url() + f'/odoo/{thread_message.model}/{thread_message.res_id}?highlight_message_id={thread_message.id}'
            res = self.url_open(f'/mail/message/{thread_message.id}')
            self.assertEqual(res.url, expected_url)
        with self.subTest(deleted_message=deleted_message):
            res = self.url_open(f'/mail/message/{deleted_message.id}')

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

        cls.alias_record = cls.env['mail.test.container'].with_context(cls._test_context).create({
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
        note_subtype = self.env.ref('mail.mt_note')
        _attach_1 = self.env['ir.attachment'].with_user(self.user_employee).create({
            'name': 'Attach1',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
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
        message.write({'starred_partner_ids': [(4, self.partner_admin.id)]})

        # check content
        self.assertEqual(len(message.attachment_ids), 1)
        self.assertFalse(is_html_empty(message.body))
        self.assertEqual(len(message.sudo().notification_ids), 1)
        self.assertEqual(message.notified_partner_ids, self.partner_admin)
        self.assertEqual(message.starred_partner_ids, self.partner_admin)
        self.assertFalse(message.sudo().tracking_value_ids)

        # Reset body case
        record._message_update_content(message, Markup('<p><br /></p>'), attachment_ids=message.attachment_ids.ids)
        self.assertTrue(is_html_empty(message.body))
        self.assertFalse(message.sudo()._filter_empty(), 'Still having attachments')

        # Subtype content
        note_subtype.sudo().write({'description': 'Very important discussions'})
        record._message_update_content(message, '', [])
        self.assertFalse(message.attachment_ids)
        self.assertEqual(message.notified_partner_ids, self.partner_admin)
        self.assertEqual(message.starred_partner_ids, self.partner_admin)
        self.assertFalse(message.sudo()._filter_empty(), 'Subtype with description')

        # Completely void now
        note_subtype.sudo().write({'description': ''})
        self.assertEqual(message.sudo()._filter_empty(), message)
        record._message_update_content(message, '', [])
        self.assertFalse(message.notified_partner_ids)
        self.assertFalse(message.starred_partner_ids)

        # test tracking values
        record.write({'user_id': self.user_admin.id})
        self.flush_tracking()
        tracking_message = record.message_ids[0]
        self.assertFalse(tracking_message.attachment_ids)
        self.assertTrue(is_html_empty(tracking_message.body))
        self.assertFalse(tracking_message.subtype_id.description)
        self.assertFalse(tracking_message.sudo()._filter_empty(), 'Has tracking values')
        with self.assertRaises(UserError, msg='Tracking values prevent from updating content'):
            record._message_update_content(tracking_message, '', [])

    @mute_logger('odoo.models.unlink')
    def test_mail_message_to_store_access(self):
        """
        User that doesn't have access to a record should still be able to fetch
        the record_name inside message _to_store.
        """
        company_2 = self.env['res.company'].create({'name': 'Second Test Company'})
        record1 = self.env['mail.test.multi.company'].create({
            'name': 'Test1',
            'company_id': company_2.id,
        })
        message = record1.message_post(body='', partner_ids=[self.user_employee.partner_id.id])
        # We need to flush and invalidate the ORM cache since the record_name
        # is already cached from the creation. Otherwise it will leak inside
        # message _to_store.
        self.env.flush_all()
        self.env.invalidate_all()
        res = Store(message.with_user(self.user_employee), for_current_user=True).get_result()
        self.assertEqual(res["mail.message"][0].get("record_name"), "Test1")

        record1.write({"name": "Test2"})
        self.env.flush_all()
        self.env.invalidate_all()
        res = Store(message.with_user(self.user_employee), for_current_user=True).get_result()
        self.assertEqual(res["mail.message"][0].get('record_name'), 'Test2')

        # check model not inheriting from mail.thread -> should not crash
        record_nothread = self.env['mail.test.nothread'].create({'name': 'NoThread'})
        message = self.env['mail.message'].create({
            'model': record_nothread._name,
            'res_id': record_nothread.id,
        })
        formatted = Store(message, for_current_user=True).get_result()["mail.message"][0]
        self.assertEqual(formatted['record_name'], record_nothread.name)

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
        records_by_model_name = next(iter(messages))._records_by_model_name()
        test_simple_records = records_by_model_name["mail.test.simple"]
        self.assertEqual(test_simple_records, record1)
        self.assertEqual(test_simple_records._prefetch_ids, tuple((record1 + record2).ids))
        record_by_message = next(iter(messages))._record_by_message()
        m0_records = record_by_message[messages[0]]
        self.assertEqual(m0_records, record1)
        self.assertEqual(m0_records._prefetch_ids, tuple((record1 + record2).ids))

    def test_mail_message_values_body_base64_image(self):
        msg = self.env['mail.message'].with_user(self.user_employee).create({
            'body': 'taratata <img src="data:image/png;base64,iV/+OkI=" width="2"> <img src="data:image/png;base64,iV/+OkI=" width="2">',
        })
        self.assertEqual(len(msg.attachment_ids), 1)
        self.assertEqual(
            msg.body,
            '<p>taratata <img src="/web/image/{attachment.id}?access_token={attachment.access_token}" alt="image0" width="2"> '
            '<img src="/web/image/{attachment.id}?access_token={attachment.access_token}" alt="image0" width="2"></p>'.format(attachment=msg.attachment_ids[0])
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
        test_record.write({
            'name': 'Super Long Name That People May Enter "Even with an internal quoting of stuff"'
        })
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        reply_to_email = f"{test_record.alias_name}@{self.alias_domain}"
        self.assertEqual(msg.reply_to, reply_to_email,
                         'Reply-To: use only email when formataddr > 68 chars')

        # name + company_name would make it blow up: keep record_name in formatting
        self.company_admin.name = "Company name being about 33 chars"
        test_record.write({'name': 'Being more than 68 with company name'})
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, formataddr((test_record.name, reply_to_email)),
                         'Reply-To: use recordname as name in format if recordname + company > 68 chars')

        # no record_name: keep company_name in formatting if ok
        test_record.write({'name': ''})
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, formataddr((self.env.user.company_id.name, reply_to_email)),
                         'Reply-To: use company as name in format when no record name and still < 68 chars')

        # no record_name and company_name make it blow up: keep only email
        self.env.user.company_id.write({'name': 'Super Long Name That People May Enter "Even with an internal quoting of stuff"'})
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, reply_to_email,
                         'Reply-To: use only email when formataddr > 68 chars')

        # whatever the record and company names, email is too long: keep only email
        test_record.write({
            'alias_name': 'Waaaay too long alias name that should make any reply-to blow the 68 characters limit',
            'name': 'Short',
        })
        self.env.user.company_id.write({'name': 'Comp'})
        sanitized_alias_name = 'waaaay-too-long-alias-name-that-should-make-any-reply-to-blow-the-68-characters-limit'
        msg = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id
        })
        self.assertEqual(msg.reply_to, f"{sanitized_alias_name}@{self.alias_domain}",
                         'Reply-To: even a long email is ok as only formataddr is problematic')

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_no_document_values(self):
        msg = self.Message.create({
            'reply_to': 'test.reply@example.com',
            'email_from': 'test.from@example.com',
        })
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, 'test.reply@example.com')
        self.assertEqual(msg.email_from, 'test.from@example.com')

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_no_document(self):
        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        reply_to_name = self.env.user.company_id.name
        reply_to_email = '%s@%s' % (self.alias_catchall, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias domain -> author
        self.env.company.alias_domain_id = False
        self.assertFalse(self.env.company.catchall_email)

        msg = self.Message.create({})
        self.assertIn('-private', msg.message_id.split('@')[0], 'mail_message: message_id for a void message should be a "private" one')
        self.assertEqual(msg.reply_to, formataddr((self.user_employee.name, self.user_employee.email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_document_alias(self):
        msg = self.Message.create({
            'model': 'mail.test.container',
            'res_id': self.alias_record.id
        })
        self.assertIn('-openerp-%d-mail.test' % self.alias_record.id, msg.message_id.split('@')[0])
        reply_to_name = '%s %s' % (self.env.user.company_id.name, self.alias_record.name)
        reply_to_email = '%s@%s' % (self.alias_record.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

        # no alias domain, no company catchall -> author
        self.alias_record.alias_domain_id = False
        self.env.company.alias_domain_id = False
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
        reply_to_name = '%s %s' % (self.env.company.name, self.alias_record.name)
        reply_to_email = '%s@%s' % (self.alias_record.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_document_no_alias(self):
        test_record = self.env['mail.test.simple'].create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        msg = self.Message.create({
            'model': 'mail.test.simple',
            'res_id': test_record.id
        })
        self.assertIn('-openerp-%d-mail.test.simple' % test_record.id, msg.message_id.split('@')[0])
        reply_to_name = '%s %s' % (self.env.user.company_id.name, test_record.name)
        reply_to_email = '%s@%s' % (self.alias_catchall, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

    @mute_logger('odoo.models.unlink')
    def test_mail_message_values_fromto_document_manual_alias(self):
        test_record = self.env['mail.test.simple'].create({'name': 'Test', 'email_from': 'ignasse@example.com'})
        alias = self.env['mail.alias'].create({
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
        reply_to_name = '%s %s' % (self.env.user.company_id.name, test_record.name)
        reply_to_email = '%s@%s' % (alias.alias_name, self.alias_domain)
        self.assertEqual(msg.reply_to, formataddr((reply_to_name, reply_to_email)))
        self.assertEqual(msg.email_from, formataddr((self.user_employee.name, self.user_employee.email)))

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
