# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Datetime as FieldDatetime
from odoo.tests import tagged, users


@tagged('mail_scheduled_message')
class TestScheduledMessage(MailCommon, TestRecipients):
    """ Test Scheduled Message internals """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # force 'now' to ease test about schedulers
        cls.reference_now = FieldDatetime.to_datetime('2022-12-24 12:00:00')

        with cls.mock_datetime_and_now(cls, cls.reference_now):
            cls.test_record = cls.env['mail.test.ticket'].with_context(cls._test_context).create([{
                'name': 'Test Record',
                'customer_id': cls.partner_1.id,
                'user_id': cls.user_employee.id,
            }])
            cls.hidden_scheduled_message, cls.visible_scheduled_message = cls.env['mail.scheduled.message'].create([
                {
                    'author_id': cls.partner_admin.id,
                    'model': cls.partner_employee._name,
                    'res_id': cls.partner_employee.id,
                    'body': 'Hidden Scheduled Message',
                    'scheduled_date': '2022-12-24 15:00:00',
                },
                {
                    'author_id': cls.partner_admin.id,
                    'model': cls.test_record._name,
                    'res_id': cls.test_record.id,
                    'body': 'Visible Scheduled Message',
                    'scheduled_date': '2022-12-24 15:00:00',
                },
            ]).with_user(cls.user_employee)

    def schedule_message(self, target_record=None, author_id=None, **kwargs):
        with self.mock_datetime_and_now(self.reference_now):
            return self.env['mail.scheduled.message'].create({
                'author_id': author_id or self.env.user.partner_id.id,
                'model': target_record._name if target_record else kwargs.pop('model'),
                'res_id': target_record.id if target_record else kwargs.pop('res_id'),
                'body': kwargs.pop('body', 'Test Body'),
                'scheduled_date': kwargs.pop('scheduled_date', '2022-12-24 15:00:00'),
                **kwargs,
            })


class TestScheduledMessageAccess(TestScheduledMessage):

    @users('employee')
    def test_scheduled_message_model_without_post_right(self):
        # creation on a record that the user cannot post to
        with self.assertRaises(AccessError):
            self.schedule_message(self.partner_employee)
        # read a message scheduled on a record the user can't post to
        with self.assertRaises(AccessError):
            self.hidden_scheduled_message.read()
        # search a message scheduled on a record the user can't post to
        self.assertFalse(self.env['mail.scheduled.message'].search([['id', '=', self.hidden_scheduled_message.id]]))
        # write on a message scheduled on a record the user can't post to
        with self.assertRaises(AccessError):
            self.hidden_scheduled_message.write({'body': 'boum'})
        # post a message scheduled on a record the user can't post to
        with self.assertRaises(AccessError):
            self.hidden_scheduled_message.post_message()
        # unlink a message scheduled on a record the user can't post to
        with self.assertRaises(AccessError):
            self.hidden_scheduled_message.unlink()

    @users('employee')
    def test_scheduled_message_model_with_post_right(self):
        # read a message scheduled by another user on a record the user can post to
        self.visible_scheduled_message.read()
        # search a message scheduled by another user on a record the user can post to
        self.assertEqual(self.env['mail.scheduled.message'].search([['id', '=', self.visible_scheduled_message.id]]), self.visible_scheduled_message)
        # write on a message scheduled by another user on a record the user can post to
        with self.assertRaises(AccessError):
            self.visible_scheduled_message.write({'body': 'boum'})
        # post a message scheduled on a record the user can post to
        with self.assertRaises(UserError):
            self.visible_scheduled_message.post_message()
        # unlink a message scheduled on a record the user can post to
        self.visible_scheduled_message.unlink()

    @users('employee')
    def test_own_scheduled_message(self):
        # create a scheduled message on a record the user can post to
        scheduled_message = self.schedule_message(self.test_record)
        # read own scheduled message
        scheduled_message.read()
        # search own scheduled message
        self.assertEqual(self.env['mail.scheduled.message'].search([['id', '=', scheduled_message.id]]), scheduled_message)
        # write on own scheduled message
        scheduled_message.write({'body': 'Hello!'})
        # unlink own scheduled message
        scheduled_message.unlink()


class TestScheduledMessageBusiness(TestScheduledMessage, CronMixinCase):

    @users('employee')
    def test_scheduled_message_restrictions(self):
        # cannot schedule a message in the past
        with self.assertRaises(ValidationError):
            self.schedule_message(self.test_record, scheduled_date='2022-12-24 10:00:00')
        # cannot schedule a message on a model without thread
        # with admin as employee does not have write access on res.users)
        with self.with_user("admin"), self.assertRaises(ValidationError):
            self.schedule_message(self.user_employee)
        scheduled_message = self.schedule_message(self.test_record)
        # cannot reschedule a message in the past
        with self.assertRaises(ValidationError):
            scheduled_message.write({'scheduled_date': '2022-12-24 14:00:00'})
        # cannot change target record of scheduled message
        with self.assertRaises(UserError):
            scheduled_message.write({'res_id': 2})
        with self.assertRaises(UserError):
            scheduled_message.write({'model': 'mail.test.track'})

    @users('employee')
    def test_scheduled_message_posting(self):
        schedule_cron_id = self.env.ref('mail.ir_cron_post_scheduled_message').id
        with self.mock_mail_gateway(), \
            self.mock_mail_app(), \
            self.capture_triggers(schedule_cron_id) as capt:
            scheduled_message_id = self.schedule_message(
                self.test_record,
                scheduled_date='2022-12-24 14:00:00',
                partner_ids=self.test_record.customer_id,
            ).id
            # cron should be triggered at scheduled date
            self.assertEqual(capt.records['call_at'], FieldDatetime.to_datetime('2022-12-24 14:00:00'))
            # no message created or mail sent
            self.assertFalse(self.test_record.message_ids)
            self.assertFalse(self._new_mails)

            with self.mock_datetime_and_now('2022-12-24 14:00:00'):
                self.env['mail.scheduled.message'].sudo()._post_messages_cron()
            # message should be posted and mail should be sent
            self.assertEqual(len(self.test_record.message_ids), 1)
            self.assertEqual(len(self._new_mails), 1)
            self.assertEqual(self._new_mails[0].state, 'sent')
            # scheduled message shouldn't exist anymore
            self.assertFalse(self.env['mail.scheduled.message'].search([['id', '=', scheduled_message_id]]))
