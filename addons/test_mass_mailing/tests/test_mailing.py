# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.data.mail_test_data import MAIL_TEMPLATE
from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger, email_normalize


@tagged('mass_mailing')
class TestMassMailing(TestMassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailing, cls).setUpClass()

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_mailing_gateway_reply(self):
        customers = self.env['res.partner']
        for x in range(0, 3):
            customers |= self.env['res.partner'].create({
                'name': 'Customer_%02d' % x,
                'email': '"Customer_%02d" <customer_%02d@test.example.com' % (x, x),
            })

        mailing = self.env['mailing.mailing'].create({
            'name': 'TestName',
            'subject': 'TestSubject',
            'body_html': 'Hello <t t-out="object.name" />',
            'reply_to_mode': 'new',
            'reply_to': '%s@%s' % (self.test_alias.alias_name, self.test_alias.alias_domain),
            'keep_archives': True,
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_domain': '%s' % [('id', 'in', customers.ids)],
        })
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        self.gateway_mail_reply_wrecord(MAIL_TEMPLATE, customers[0], use_in_reply_to=True)
        self.gateway_mail_reply_wrecord(MAIL_TEMPLATE, customers[1], use_in_reply_to=False)

        # customer2 looses headers
        mail_mail = self._find_mail_mail_wrecord(customers[2])
        self.format_and_process(
            MAIL_TEMPLATE,
            mail_mail.email_to,
            mail_mail.reply_to,
            subject='Re: %s' % mail_mail.subject,
            extra='',
            msg_id='<123456.%s.%d@test.example.com>' % (customers[2]._name, customers[2].id),
            target_model=customers[2]._name, target_field=customers[2]._rec_name,
        )
        mailing.flush_recordset()

        # check traces status
        traces = self.env['mailing.trace'].search([('model', '=', customers._name), ('res_id', 'in', customers.ids)])
        self.assertEqual(len(traces), 3)
        customer0_trace = traces.filtered(lambda t: t.res_id == customers[0].id)
        self.assertEqual(customer0_trace.trace_status, 'reply')
        customer1_trace = traces.filtered(lambda t: t.res_id == customers[1].id)
        self.assertEqual(customer1_trace.trace_status, 'reply')
        customer2_trace = traces.filtered(lambda t: t.res_id == customers[2].id)
        self.assertEqual(customer2_trace.trace_status, 'sent')

        # check mailing statistics
        self.assertEqual(mailing.sent, 3)
        self.assertEqual(mailing.delivered, 3)
        self.assertEqual(mailing.opened, 2)
        self.assertEqual(mailing.replied, 2)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_gateway_update(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        recipients = self._create_mailing_test_records(model='mailing.test.optout', count=5)
        self.assertEqual(len(recipients), 5)

        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout'),
            'mailing_domain': [('id', 'in', recipients.ids)]
        })
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        self.assertMailTraces(
            [{
                'email': record.email_normalized,
                'email_to_mail': record.email_from,
             } for record in recipients],
            mailing, recipients,
            mail_links_info=[[
                ('url0', 'https://www.odoo.tz/my/%s' % record.name, True, {}),
                ('url1', 'https://www.odoo.be', True, {}),
                ('url2', 'https://www.odoo.com', True, {}),
                ('url3', 'https://www.odoo.eu', True, {}),
                ('url4', 'https://www.example.com/foo/bar?baz=qux', True, {'baz': 'qux'}),
                ('url5', '%s/event/dummy-event-0' % mailing.get_base_url(), True, {}),
                # view is not shortened and parsed at sending
                ('url6', '%s/view' % mailing.get_base_url(), False, {}),
                ('url7', 'mailto:test@odoo.com', False, {}),
                # unsubscribe is not shortened and parsed at sending
                ('url8', '%s/unsubscribe_from_list' % mailing.get_base_url(), False, {}),
            ] for record in recipients],
            check_mail=True
        )
        self.assertMailingStatistics(mailing, expected=5, delivered=5, sent=5)

        # simulate a click
        self.gateway_mail_trace_click(mailing, recipients[0], 'https://www.odoo.be')
        mailing.invalidate_recordset()
        self.assertMailingStatistics(mailing, expected=5, delivered=5, sent=5, opened=1, clicked=1)

        # simulate a bounce
        self.assertEqual(recipients[1].message_bounce, 0)
        self.gateway_mail_trace_bounce(mailing, recipients[1])
        mailing.invalidate_recordset()
        self.assertMailingStatistics(mailing, expected=5, delivered=4, sent=5, opened=1, clicked=1, bounced=1)
        self.assertEqual(recipients[1].message_bounce, 1)
        self.assertMailTraces([{
            'email': 'test.record.01@test.example.com',
            'email_to_mail': recipients[1].email_from,
            'failure_reason': 'This is the bounce email',
            'failure_type': 'mail_bounce',
            'trace_status': 'bounce',
        }], mailing, recipients[1], check_mail=False)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_recipients(self):
        """ Test recipient-specific computation, with email, formatting,
        multi-emails, ... to test corner cases. Blacklist mixin impact is
        tested. """
        (customer_mult, customer_fmt, customer_unic,
         customer_case, customer_weird, customer_weird_2
        ) = self.env['res.partner'].create([
            {
                'email': 'customer.multi.1@example.com, "Test Multi 2" <customer.multi.2@example.com>',
                'name': 'MultiEMail',
            }, {
                'email': '"Formatted Customer" <test.customer.format@example.com>',
                'name': 'FormattedEmail',
            }, {
                'email': '"Unicode Customer" <test.customer.😊@example.com>',
                'name': 'UnicodeEmail',
            }, {
                'email': 'TEST.CUSTOMER.CASE@EXAMPLE.COM',
                'name': 'CaseEmail',
            }, {
                'email': 'test.customer.weird@example.com Weird Format',
                'name': 'WeirdFormatEmail',
            }, {
                'email': 'Weird Format2 test.customer.weird.2@example.com',
                'name': 'WeirdFormatEmail2',
            }
        ])

        # check difference of email management between a classic model and a model
        # with an 'email_normalized' field (blacklist mixin)
        for dst_model in ['mailing.test.customer', 'mailing.test.blacklist']:
            with self.subTest(dst_model=dst_model):
                (record_p_mult, record_p_fmt, record_p_unic,
                 record_p_case, record_p_weird, record_p_weird_2,
                 record_mult, record_fmt, record_unic,
                 record_case, recod_weird, record_weird_2
                ) = self.env[dst_model].create([
                    {
                        'customer_id': customer_mult.id,
                    }, {
                        'customer_id': customer_fmt.id,
                    }, {
                        'customer_id': customer_unic.id,
                    }, {
                        'customer_id': customer_case.id,
                    }, {
                        'customer_id': customer_weird.id,
                    }, {
                        'customer_id': customer_weird_2.id,
                    }, {
                        'email_from': 'record.multi.1@example.com, "Record Multi 2" <record.multi.2@example.com>',
                    }, {
                        'email_from': '"Formatted Record" <record.format@example.com>',
                    }, {
                        'email_from': '"Unicode Record" <record.😊@example.com>',
                    }, {
                        'email_from': 'TEST.RECORD.CASE@EXAMPLE.COM',
                    }, {
                        'email_from': 'test.record.weird@example.com Weird Format',
                    }, {
                        'email_from': 'Weird Format2 test.record.weird.2@example.com',
                    }
                ])
                test_records = (
                    record_p_mult + record_p_fmt + record_p_unic +
                    record_p_case + record_p_weird + record_p_weird_2 +
                    record_mult + record_fmt + record_unic +
                    record_case + recod_weird + record_weird_2
                )
                mailing = self.env['mailing.mailing'].create({
                    'body_html': """<div><p>Hello ${object.name}</p>""",
                    'mailing_domain': [('id', 'in', test_records.ids)],
                    'mailing_model_id': self.env['ir.model']._get_id(dst_model),
                    'mailing_type': 'mail',
                    'name': 'SourceName',
                    'preview': 'Hi ${object.name} :)',
                    'reply_to_mode': 'update',
                    'subject': 'MailingSubject',
                })

                with self.mock_mail_gateway(mail_unlink_sent=False):
                    mailing.action_send_mail()

                # Difference in email, email_to_recipients and email_to_mail
                # -> email: trace email: normalized, to ease its management, mainly technical
                # -> email_to_mail: mail.mail email: email_to stored in outgoing mail.mail (can be multi)
                # -> email_to_recipients: email_to for outgoing emails, list means several recipients
                self.assertMailTraces(
                    [
                        {'email': 'customer.multi.1@example.com',
                         'email_to_mail': False,  # using recipient_ids, not email_to
                         'email_to_recipients': [[f'"{customer_mult.name}" <customer.multi.1@example.com>', f'"{customer_mult.name}" <customer.multi.2@example.com>']],
                         'failure_type': False,
                         'partner': customer_mult,
                         'trace_status': 'sent'},
                        {'email': 'test.customer.format@example.com',
                         'email_to_mail': False,  # using recipient_ids, not email_to
                         # mail to avoids double encapsulation
                         'email_to_recipients': [[f'"{customer_fmt.name}" <test.customer.format@example.com>']],
                         'failure_type': False,
                         'partner': customer_fmt,
                         'trace_status': 'sent'},
                        {'email': 'test.customer.😊@example.com',
                         'email_to_mail': False,  # using recipient_ids, not email_to
                         # mail to avoids double encapsulation
                         'email_to_recipients': [[f'"{customer_unic.name}" <test.customer.😊@example.com>']],
                         'failure_type': False,
                         'partner': customer_unic,
                         'trace_status': 'sent'},
                        {'email': 'test.customer.case@example.com',
                         'email_to_mail': False,  # using recipient_ids, not email_to
                         'email_to_recipients': [[f'"{customer_case.name}" <test.customer.case@example.com>']],
                         'failure_type': False,
                         'partner': customer_case,
                         'trace_status': 'sent'},  # lower cased
                        {'email': 'test.customer.weird@example.comweirdformat',
                         'email_to_mail': False,  # using recipient_ids, not email_to
                         'email_to_recipients': [[f'"{customer_weird.name}" <test.customer.weird@example.comweirdformat>']],
                         'failure_type': False,
                         'partner': customer_weird,
                         'trace_status': 'sent'},  # concatenates everything after domain
                        {'email': 'test.customer.weird.2@example.com',
                         'email_to_mail': False,  # using recipient_ids, not email_to
                         'email_to_recipients': [[f'"{customer_weird_2.name}" <test.customer.weird.2@example.com>']],
                         'failure_type': False,
                         'partner': customer_weird_2,
                         'trace_status': 'sent'},
                        {'email': 'record.multi.1@example.com',
                         'email_to_mail': 'record.multi.1@example.com,"Record Multi 2" <record.multi.2@example.com>',
                         'email_to_recipients': [['record.multi.1@example.com', '"Record Multi 2" <record.multi.2@example.com>']],
                         'failure_type': False,
                         'trace_status': 'sent'},
                        {'email': 'record.format@example.com',
                         'email_to_mail': '"Formatted Record" <record.format@example.com>',
                         'email_to_recipients': [['"Formatted Record" <record.format@example.com>']],
                         'failure_type': False,
                         'trace_status': 'sent'},
                        {'email': 'record.😊@example.com',
                         'email_to_mail': '"Unicode Record" <record.😊@example.com>',
                         'email_to_recipients': [['"Unicode Record" <record.😊@example.com>']],
                         'failure_type': False,
                         'trace_status': 'sent'},
                        {'email': 'test.record.case@example.com',
                         'email_to_mail': 'test.record.case@example.com',
                         'email_to_recipients': [['test.record.case@example.com']],
                         'failure_type': False,
                         'trace_status': 'sent'},
                        {'email': 'test.record.weird@example.comweirdformat',
                         'email_to_mail': 'test.record.weird@example.comweirdformat',
                         'email_to_recipients': [['test.record.weird@example.comweirdformat']],
                         'failure_type': False,
                         'trace_status': 'sent'},
                        {'email': 'test.record.weird.2@example.com',
                         'email_to_mail': '"Weird Format2" <test.record.weird.2@example.com>',
                         'email_to_recipients': [['"Weird Format2" <test.record.weird.2@example.com>']],
                         'failure_type': False,
                         'trace_status': 'sent'},
                    ],
                    mailing,
                    test_records,
                    check_mail=True,
                )

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_reply_to_mode_new(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        recipients = self._create_mailing_test_records(model='mailing.test.blacklist', count=5)
        self.assertEqual(len(recipients), 5)
        initial_messages = recipients.message_ids
        mailing.write({
            'mailing_domain': [('id', 'in', recipients.ids)],
            'keep_archives': False,
            'reply_to_mode': 'new',
            'reply_to': self.test_alias.display_name,
        })

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        answer_rec = self.gateway_mail_reply_wemail(
            MAIL_TEMPLATE,
            recipients[0].email_from,
            target_model=self.test_alias.alias_model_id.model,
        )
        self.assertTrue(bool(answer_rec))
        self.assertEqual(answer_rec.name, 'Re: %s' % mailing.subject)
        self.assertEqual(
            answer_rec.message_ids.subject, 'Re: %s' % mailing.subject,
            'Answer should be logged')
        self.assertEqual(recipients.message_ids, initial_messages)

        self.assertMailingStatistics(mailing, expected=5, delivered=5, sent=5, opened=1, replied=1)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_reply_to_mode_update(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        recipients = self._create_mailing_test_records(model='mailing.test.blacklist', count=5)
        self.assertEqual(len(recipients), 5)
        mailing.write({
            'mailing_domain': [('id', 'in', recipients.ids)],
            'keep_archives': False,
            'reply_to_mode': 'update',
            'reply_to': self.test_alias.display_name,
        })

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        answer_rec = self.gateway_mail_reply_wemail(
            MAIL_TEMPLATE,
            recipients[0].email_from,
            target_model=self.test_alias.alias_model_id.model,
        )
        self.assertFalse(bool(answer_rec))
        self.assertEqual(
            recipients[0].message_ids[1].subject, mailing.subject,
            'Should have keep a log (to enable thread-based answer)')
        self.assertEqual(
            recipients[0].message_ids[0].subject, 'Re: %s' % mailing.subject,
            'Answer should be logged')

        self.assertMailingStatistics(mailing, expected=5, delivered=5, sent=5, opened=1, replied=1)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_mailing_trace_utm(self):
        """ Test mailing UTMs are caught on reply"""
        self._create_mailing_list()
        self.test_alias.write({
            'alias_model_id': self.env['ir.model']._get('mailing.test.utm').id
        })

        source = self.env['utm.source'].create({'name': 'Source test'})
        medium = self.env['utm.medium'].create({'name': 'Medium test'})
        campaign = self.env['utm.campaign'].create({'name': 'Campaign test'})
        subject = 'MassMailingTestUTM'

        mailing = self.env['mailing.mailing'].create({
            'name': 'UTMTest',
            'subject': subject,
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'reply_to_mode': 'new',
            'reply_to': '%s@%s' % (self.test_alias.alias_name, self.test_alias.alias_domain),
            'keep_archives': True,
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [(4, self.mailing_list_1.id)],
            'source_id': source.id,
            'medium_id': medium.id,
            'campaign_id': campaign.id
        })

        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        traces = self.env['mailing.trace'].search([('model', '=', self.mailing_list_1.contact_ids._name), ('res_id', 'in', self.mailing_list_1.contact_ids.ids)])
        self.assertEqual(len(traces), 3)

        # simulate response to mailing
        self.gateway_mail_reply_wrecord(MAIL_TEMPLATE, self.mailing_list_1.contact_ids[0], use_in_reply_to=True)
        self.gateway_mail_reply_wrecord(MAIL_TEMPLATE, self.mailing_list_1.contact_ids[1], use_in_reply_to=False)

        mailing_test_utms = self.env['mailing.test.utm'].search([('name', '=', 'Re: %s' % subject)])
        self.assertEqual(len(mailing_test_utms), 2)
        for test_utm in mailing_test_utms:
            self.assertEqual(test_utm.campaign_id, campaign)
            self.assertEqual(test_utm.source_id, source)
            self.assertEqual(test_utm.medium_id, medium)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_w_blacklist(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        recipients = self._create_mailing_test_records(count=5)

        # blacklist records 2, 3, 4
        self.env['mail.blacklist'].create({'email': recipients[2].email_normalized})
        self.env['mail.blacklist'].create({'email': recipients[3].email_normalized})
        self.env['mail.blacklist'].create({'email': recipients[4].email_normalized})

        # unblacklist record 2
        self.env['mail.blacklist']._remove(
            recipients[2].email_normalized, message="human error"
        )
        self.env['mail.blacklist'].flush_model(['active'])

        mailing.write({'mailing_domain': [('id', 'in', recipients.ids)]})
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        self.assertMailTraces(
            [{
                'email': record.email_normalized,
                'email_to_mail': record.email_from,
            } for record in recipients[:3]] + [{
                'email': record.email_normalized,
                'email_to_mail': record.email_from,
                'failure_type': 'mail_bl',
                'trace_status': 'cancel',
            } for record in recipients[3:]],
            mailing, recipients, check_mail=True
        )
        self.assertEqual(mailing.canceled, 2)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_w_blacklist_nomixin(self):
        """Test that blacklist is applied even if the target model doesn't inherit
        from mail.thread.blacklist."""
        test_records = self._create_mailing_test_records(model='mailing.test.simple', count=2)
        self.mailing_bl.write({
            'mailing_domain': [('id', 'in', test_records.ids)],
            'mailing_model_id': self.env['ir.model']._get('mailing.test.simple').id,
        })
        self.env['mail.blacklist'].create([{
            'email': test_records[0].email_from,
            'active': True,
        }])

        with self.mock_mail_gateway(mail_unlink_sent=False):
            self.mailing_bl.action_send_mail()
        self.assertMailTraces([
            {'email': email_normalize(test_records[0].email_from), 'trace_status': 'cancel', 'failure_type': 'mail_bl'},
            {'email': email_normalize(test_records[1].email_from), 'trace_status': 'sent'},
        ], self.mailing_bl, test_records, check_mail=False)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_w_opt_out(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        recipients = self._create_mailing_test_records(model='mailing.test.optout', count=5)

        # optout records 0 and 1
        (recipients[0] | recipients[1]).write({'opt_out': True})
        # blacklist records 4
        self.env['mail.blacklist'].create({'email': recipients[4].email_normalized})

        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout'),
            'mailing_domain': [('id', 'in', recipients.ids)]
        })
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        self.assertMailTraces(
            [{
                'email': record.email_normalized,
                'email_to_mail': record.email_from,
                'failure_type': 'mail_optout',
                'trace_status': 'cancel',
            } for record in recipients[:2]] + [{
                'email': record.email_normalized,
                'email_to_mail': record.email_from,
            } for record in recipients[2:4]] + [{
                'email': record.email_normalized,
                'email_to_mail': record.email_from,
                'failure_type': 'mail_bl',
                'trace_status': 'cancel'
            } for record in recipients[4:]],
            mailing, recipients, check_mail=True
        )
        self.assertEqual(mailing.canceled, 3)

    @users('user_marketing')
    def test_mailing_w_seenlist(self):
        """
        Tests whether function `_get_seen_list` is correctly able to identify duplicate emails,
        even through different batches.
        Mails use different names to make sure they are recognized as duplicates even without being
        normalized (e.g.: '"jc" <0@example.com>' and '"vd" <0@example.com>' are duplicates)
        """
        BATCH_SIZE = 5
        names = ['jc', 'vd']
        emails = [f'test.{i}@example.com' for i in range(BATCH_SIZE)]
        records = self.env['mailing.test.partner'].create([{
            'name': f'test_duplicates {i}', 'email_from': f'"{names[i % 2]}" <{emails[i % BATCH_SIZE]}>'
        } for i in range(20)])

        mailing = self.env['mailing.mailing'].create({
            'mailing_domain': [('name', 'ilike', 'test_duplicates %')],
            'mailing_model_id': self.env.ref('test_mass_mailing.model_mailing_test_partner').id,
            'name': 'test duplicates',
            'subject': 'test duplicates',
        })

        with self.mock_mail_gateway():
            for i in range(0, 20, BATCH_SIZE):
                mailing.action_send_mail(records[i:i + BATCH_SIZE]._ids)
            self.assertEqual(len(self._mails), BATCH_SIZE)
            self.assertEqual(mailing.canceled, 15)
            mails_sent = [email_normalize(mail['email_to'][0]) for mail in self._mails]
            for email in emails:
                self.assertEqual(mails_sent.count(email), 1)

    @users('user_marketing')
    def test_mailing_w_seenlist_unstored_partner(self):
        """ Test seen list when partners are not stored. """
        test_customers = self.env['res.partner'].sudo().create([
            {'email': f'"Mailing Partner {idx}" <email.from.{idx}@test.example.com',
             'name': f'Mailing Partner {idx}',
            } for idx in range(8)
        ])
        test_records = self.env['mailing.test.partner.unstored'].create([
            {'email_from': f'email.from.{idx}@test.example.com',
             'name': f'Mailing Record {idx}',
            } for idx in range(10)
        ])
        self.assertEqual(test_records[:8].partner_id, test_customers)
        self.assertFalse(test_records[9:].partner_id)

        mailing = self.env['mailing.mailing'].create({
            'body_html': '<p>Marketing stuff for ${object.name}</p>',
            'mailing_domain': [('id', 'in', test_records.ids)],
            'mailing_model_id': self.env['ir.model']._get_id('mailing.test.partner.unstored'),
            'name': 'test',
            'subject': 'Blacklisted',
        })

        # create existing traces to check the seen list
        traces = self._create_sent_traces(
            mailing,
            test_records[:3]
        )
        traces.flush_model()

        # check remaining recipients effectively check seen list
        mailing.action_put_in_queue()
        res_ids = mailing._get_remaining_recipients()
        self.assertEqual(sorted(res_ids), sorted(test_records[3:].ids))

        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()
        self.assertEqual(len(self._mails), 7, 'Mailing: seen list should contain 3 existing traces')

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_mailing_list_optout(self):
        """ Test mailing list model specific optout behavior """
        # as duplication checks body and subject, we create 2 exact copies to make sure only 1 is sent
        mailing_contact_1 = self.env['mailing.contact'].create({'name': 'test 1', 'email': 'test@test.example.com'})
        mailing_contact_2 = self.env['mailing.contact'].create({'name': 'test 1', 'email': 'test@test.example.com'})
        mailing_contact_3 = self.env['mailing.contact'].create({'name': 'test 3', 'email': 'test3@test.example.com'})
        mailing_contact_4 = self.env['mailing.contact'].create({'name': 'test 4', 'email': 'test4@test.example.com'})
        mailing_contact_5 = self.env['mailing.contact'].create({'name': 'test 5', 'email': 'test5@test.example.com'})

        # create mailing list record
        mailing_list_1 = self.env['mailing.list'].create({
            'name': 'A',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id),
                (4, mailing_contact_3.id),
                (4, mailing_contact_5.id),
            ]
        })
        mailing_list_2 = self.env['mailing.list'].create({
            'name': 'B',
            'contact_ids': [
                (4, mailing_contact_3.id),
                (4, mailing_contact_4.id),
            ]
        })
        # contact_1 is optout but same email is not optout from the same list
        # contact 3 is optout in list 1 but not in list 2
        # contact 5 is optout
        subs = self.env['mailing.subscription'].search([
            '|', '|',
            '&', ('contact_id', '=', mailing_contact_1.id), ('list_id', '=', mailing_list_1.id),
            '&', ('contact_id', '=', mailing_contact_3.id), ('list_id', '=', mailing_list_1.id),
            '&', ('contact_id', '=', mailing_contact_5.id), ('list_id', '=', mailing_list_1.id)
        ])
        subs.write({'opt_out': True})

        # create mass mailing record
        mailing = self.env['mailing.mailing'].create({
            'name': 'SourceName',
            'subject': 'MailingSubject',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [(4, ml.id) for ml in mailing_list_1 | mailing_list_2],
        })
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        self.assertMailTraces(
            [{'email': 'test@test.example.com', 'trace_status': 'sent'},
             {'email': 'test@test.example.com', 'trace_status': 'cancel', 'failure_type': 'mail_dup'},
             {'email': 'test3@test.example.com'},
             {'email': 'test4@test.example.com'},
             {'email': 'test5@test.example.com', 'trace_status': 'cancel', 'failure_type': 'mail_optout'}],
            mailing,
            # mailing_contact_1 + mailing_contact_2 + mailing_contact_3 + mailing_contact_4 + mailing_contact_5,
            mailing_contact_2 + mailing_contact_1 + mailing_contact_3 + mailing_contact_4 + mailing_contact_5,
            check_mail=True
        )
        self.assertEqual(mailing.canceled, 2)
