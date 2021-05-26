# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.data.mail_test_data import MAIL_TEMPLATE
from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


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
            'body_html': 'Hello ${object.name}',
            'reply_to_mode': 'email',
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
        mailing.flush()

        # check traces status
        traces = self.env['mailing.trace'].search([('model', '=', customers._name), ('res_id', 'in', customers.ids)])
        self.assertEqual(len(traces), 3)
        customer0_trace = traces.filtered(lambda t: t.res_id == customers[0].id)
        self.assertEqual(customer0_trace.state, 'replied')
        customer1_trace = traces.filtered(lambda t: t.res_id == customers[1].id)
        self.assertEqual(customer1_trace.state, 'replied')
        customer2_trace = traces.filtered(lambda t: t.res_id == customers[2].id)
        self.assertEqual(customer2_trace.state, 'sent')

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
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': record.email_normalized}
             for record in recipients],
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
        self.gateway_mail_click(mailing, recipients[0], 'https://www.odoo.be')
        mailing.invalidate_cache()
        self.assertMailingStatistics(mailing, expected=5, delivered=5, sent=5, opened=1, clicked=1)

        # simulate a bounce
        self.assertEqual(recipients[1].message_bounce, 0)
        self.gateway_mail_bounce(mailing, recipients[1])
        mailing.invalidate_cache()
        self.assertMailingStatistics(mailing, expected=5, delivered=4, sent=5, opened=1, clicked=1, bounced=1)
        self.assertEqual(recipients[1].message_bounce, 1)

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
            'reply_to_mode': 'email',
            'reply_to': self.test_alias.display_name,
        })

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        answer_rec = self.gateway_mail_reply_wemail(MAIL_TEMPLATE, recipients[0].email_normalized, target_model=self.test_alias.alias_model_id.model)
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
            'reply_to_mode': 'thread',
            'reply_to': self.test_alias.display_name,
        })

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        answer_rec = self.gateway_mail_reply_wemail(MAIL_TEMPLATE, recipients[0].email_normalized, target_model=self.test_alias.alias_model_id.model)
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
            'body_html': '<p>Hello ${object.name}</p>',
            'reply_to_mode': 'email',
            'reply_to': '%s@%s' % (self.test_alias.alias_name, self.test_alias.alias_domain),
            'keep_archives': True,
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [(4, self.mailing_list_1.id)],
            'source_id': source.id,
            'medium_id': medium.id,
            'campaign_id': campaign.id
        })

        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

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
        self.env['mail.blacklist'].action_remove_with_reason(
            recipients[2].email_normalized, "human error"
        )
        self.env['mail.blacklist'].flush(['active'])

        mailing.write({'mailing_domain': [('id', 'in', recipients.ids)]})
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'test.record.00@test.example.com'},
             {'email': 'test.record.01@test.example.com'},
             {'email': 'test.record.02@test.example.com'},
             {'email': 'test.record.03@test.example.com', 'state': 'ignored'},
             {'email': 'test.record.04@test.example.com', 'state': 'ignored'}],
            mailing, recipients, check_mail=True
        )
        self.assertEqual(mailing.ignored, 2)

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
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'test.record.00@test.example.com', 'state': 'ignored'},
             {'email': 'test.record.01@test.example.com', 'state': 'ignored'},
             {'email': 'test.record.02@test.example.com'},
             {'email': 'test.record.03@test.example.com'},
             {'email': 'test.record.04@test.example.com', 'state': 'ignored'}],
            mailing, recipients, check_mail=True
        )
        self.assertEqual(mailing.ignored, 3)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_mailing_list_optout(self):
        """ Test mailing list model specific optout behavior """
        mailing_contact_1 = self.env['mailing.contact'].create({'name': 'test 1A', 'email': 'test@test.example.com'})
        mailing_contact_2 = self.env['mailing.contact'].create({'name': 'test 1B', 'email': 'test@test.example.com'})
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
        Sub = self.env['mailing.contact.subscription']
        Sub.search([('contact_id', '=', mailing_contact_1.id), ('list_id', '=', mailing_list_1.id)]).write({'opt_out': True})
        Sub.search([('contact_id', '=', mailing_contact_3.id), ('list_id', '=', mailing_list_1.id)]).write({'opt_out': True})
        Sub.search([('contact_id', '=', mailing_contact_5.id), ('list_id', '=', mailing_list_1.id)]).write({'opt_out': True})

        # create mass mailing record
        mailing = self.env['mailing.mailing'].create({
            'name': 'SourceName',
            'subject': 'MailingSubject',
            'body_html': '<p>Hello ${object.name}</p>',
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [(4, ml.id) for ml in mailing_list_1 | mailing_list_2],
        })
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'test@test.example.com', 'state': 'sent'},
             {'email': 'test@test.example.com', 'state': 'ignored'},
             {'email': 'test3@test.example.com'},
             {'email': 'test4@test.example.com'},
             {'email': 'test5@test.example.com', 'state': 'ignored'}],
            mailing,
            mailing_contact_1 + mailing_contact_2 + mailing_contact_3 + mailing_contact_4 + mailing_contact_5,
            check_mail=True
        )
        self.assertEqual(mailing.ignored, 2)
