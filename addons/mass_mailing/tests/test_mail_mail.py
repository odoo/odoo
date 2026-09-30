from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import tagged


@tagged('mail_mail')
class TestMailMail(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param("mass_mailing.cancelled_mails_months_limit", 6)
        cls.env['ir.config_parameter'].sudo().set_param("mail.mail.force.send.limit", 1)  # use queue, no force_send for mass mailings here

        cls.mail_template = cls.env['mail.template'].create({
            'body_html': 'Test Mass Composer',
            'model_id': cls.env['ir.model']._get_id('res.partner'),
            'name': 'Test Mass Composer',
        })

    def test_mail_mail_gc(self):
        """ Test GC of mail.mail """
        now = datetime(2025, 12, 1, 10, 0, 0)
        partners = self.env['res.partner'].create([
            {'name': 'Real', 'email': '"I AM REAL" <test.customer@example.com>'},
            {'name': 'Ze Dupe', 'email': '"I AM DUPE" <test.customer@example.com>'},
            {'name': 'Bl', 'email': '"I AM BL" <test.customer.bl@example.com>'},
        ])
        partner_real, partner_dupe, partner_bl = partners
        self.env['mail.blacklist'].create({'email': 'test.customer.bl@example.com'})
        partners.message_ids.unlink()  # don't be annoyed by existing messages

        # do a manual mass mail, which does not skip canceled emails, without keeping
        # mail.message -> to be removed with emails
        with self.mock_datetime_and_now(now):
            mails = partners.message_mail_with_source(
                self.mail_template,
                auto_delete=True,
                auto_delete_keep_log=False,
            )
        self.assertEqual(len(mails), 3)
        for mail in mails:
            self.assertFalse(mail.is_notification, 'Messages are not kept in chatter')

        # do a manual mass mail, which keeps generated mail.messages, creating canceled
        # notification mail.mail -> messages should not be removed with emails
        with self.mock_datetime_and_now(now):
            mails_2 = partners.message_mail_with_source(
                self.mail_template,
                auto_delete=False,
                auto_delete_keep_log=True,
            )
        self.assertEqual(len(mails_2), 3)
        for mail in mails_2:
            if mail.res_id == partner_bl.id:
                self.assertFalse(mail.is_notification, 'Blacklisted emails do not appear in chatter -> is_notification set to False, to be removed')
            else:
                self.assertTrue(mail.is_notification, 'Messages are kept in chatter')
        valid_mails_2 = mails_2.filtered(lambda m: m.res_id == partner_real.id)
        chatter_msgs_2 = mails_2.filtered(lambda m: m.res_id != partner_bl.id).mail_message_id

        # now create mailing messages, which skips canceled emails
        mailing = self.env['mailing.mailing'].with_user(self.user_marketing).create({
            'body_html': 'How is your GC going ?',
            'mailing_domain': [('id', 'in', partners.ids)],
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'name': 'Test GC',
            'reply_to_mode': 'new',
            'subject': 'Test GC',
            'user_id': self.user_marketing.id,
        })
        # send it
        mailing.action_put_in_queue()
        with self.mock_datetime_and_now(now), \
             self.mock_mail_gateway(mail_unlink_sent=True), self.enter_registry_test_mode():
            self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').sudo().method_direct_trigger()
        # check generated content: 1 outgoing, 2 canceled (blacklisted and duplicate)
        email_values = {'email_from': self.user_marketing.email_formatted}
        mail_values = {'write_date': now}  # ensure write_date works as expected
        self.assertMailTraces(
            [
                {'partner': partner_real, 'trace_status': 'outgoing', 'email_values': email_values, 'mail_values': mail_values},  # mail in queue
                {'partner': partner_dupe, 'trace_status': 'cancel', 'failure_type': 'mail_dup', 'email_values': email_values, 'mail_values': mail_values},
                {'partner': partner_bl, 'trace_status': 'cancel', 'failure_type': 'mail_bl', 'email_values': email_values, 'mail_values': mail_values},
            ],
            mailing, partners,
            author=self.user_marketing.partner_id,
            check_mail=True,
            sent_unlink=False,  # should use queue, hence not sent, hence not removed
        )

        # check mail.mail current state
        all_mails = self.env['mail.mail'].search([('model', '=', partners._name), ('res_id', 'in', partners.ids)])
        self.assertEqual(len(all_mails), 7, 'Should have 2*3 mails (manual mailings) + 1 mail (not canceled in mailing)')
        all_messages = self.env['mail.message'].search([('model', '=', partners._name), ('res_id', 'in', partners.ids)])
        self.assertEqual(len(all_messages), 7, 'Should have 1 message / mail')

        # run email queue, should unlink some of them
        with self.mock_datetime_and_now(now), \
             self.mock_mail_gateway(mail_unlink_sent=True), self.enter_registry_test_mode():
            self.env['mail.mail'].process_email_queue()
        all_mails = all_mails.exists()
        self.assertEqual(len(all_mails), 5, 'Should have sent 2 emails')

        # Under "to keep" timeframe
        with self.mock_datetime_and_now(now + relativedelta(months=4)):
            self.env['mail.mail']._gc_canceled_mail_mail()
        all_mails = all_mails.exists()
        self.assertEqual(len(all_mails), 5, 'Too soon to be removed')
        # After "to keep" timeframe (see "mass_mailing.cancelled_mails_months_limit")
        with self.mock_datetime_and_now(now + relativedelta(months=7)):
            self.env['mail.mail']._gc_canceled_mail_mail()

        # What's left ? "keep archive" sent email (1, second composer), and all
        # valid messages of "keep archive" (2, second composer)
        all_mails = all_mails.exists()
        self.assertEqual(all_mails, valid_mails_2, 'Should keep only "keep archives" composer sent email')
        all_messages = all_messages.exists()
        self.assertEqual(all_messages, chatter_msgs_2, 'Should keep only "keep archives" messages (even with deleted email), without the blacklisted one')
