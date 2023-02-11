# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from datetime import datetime

from freezegun import freeze_time

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests.common import users, Form
from odoo.tools import formataddr, mute_logger

class TestMassMailValues(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailValues, cls).setUpClass()
        cls._create_mailing_list()

    @users('user_marketing')
    def test_mailing_body_responsive(self):
        """ Testing mail mailing responsive mail body

        Reference: https://litmus.com/community/learning/24-how-to-code-a-responsive-email-from-scratch
        https://www.campaignmonitor.com/css/link-element/link-in-head/

        This template is meant to put inline CSS into an email's head
        """
        recipient = self.env['res.partner'].create({
            'name': 'Mass Mail Partner',
            'email': 'Customer <test.customer@example.com>',
        })
        mailing = self.env['mailing.mailing'].create({
            'name': 'Test',
            'subject': 'Test',
            'state': 'draft',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })

        composer = self.env['mail.compose.message'].with_user(self.user_marketing).with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': 'res.partner',
            'default_res_id': recipient.id,
        }).create({
            'subject': 'Mass Mail Responsive',
            'body': 'I am Responsive body',
            'mass_mailing_id': mailing.id
        })

        mail_values = composer.get_mail_values([recipient.id])
        body_html = mail_values[recipient.id]['body_html']

        self.assertIn('<!DOCTYPE html>', body_html)
        self.assertIn('<head>', body_html)
        self.assertIn('viewport', body_html)
        # This is important: we need inline css, and not <link/>
        self.assertIn('@media', body_html)
        self.assertIn('I am Responsive body', body_html)

    @users('user_marketing')
    def test_mailing_computed_fields(self):
        # Create on res.partner, with default values for computed fields
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        self.assertEqual(mailing.user_id, self.user_marketing)
        self.assertEqual(mailing.medium_id, self.env.ref('utm.utm_medium_email'))
        self.assertEqual(mailing.mailing_model_name, 'res.partner')
        self.assertEqual(mailing.mailing_model_real, 'res.partner')
        self.assertEqual(mailing.reply_to_mode, 'new')
        self.assertEqual(mailing.reply_to, self.user_marketing.email_formatted)
        # default for partner: remove blacklisted
        self.assertEqual(literal_eval(mailing.mailing_domain), [('is_blacklisted', '=', False)])
        # update domain
        mailing.write({
            'mailing_domain': [('email', 'ilike', 'test.example.com')]
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('email', 'ilike', 'test.example.com')])

        # reset mailing model -> reset domain; set reply_to -> keep it
        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'reply_to': self.email_reply_to,
        })
        self.assertEqual(mailing.mailing_model_name, 'mailing.list')
        self.assertEqual(mailing.mailing_model_real, 'mailing.contact')
        self.assertEqual(mailing.reply_to_mode, 'new')
        self.assertEqual(mailing.reply_to, self.email_reply_to)
        # default for mailing list: depends upon contact_list_ids
        self.assertEqual(literal_eval(mailing.mailing_domain), [('list_ids', 'in', [])])
        mailing.write({
            'contact_list_ids': [(4, self.mailing_list_1.id), (4, self.mailing_list_2.id)]
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('list_ids', 'in', (self.mailing_list_1 | self.mailing_list_2).ids)])

        # reset mailing model -> reset domain and reply to mode
        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mail.channel').id,
        })
        self.assertEqual(mailing.mailing_model_name, 'mail.channel')
        self.assertEqual(mailing.mailing_model_real, 'mail.channel')
        self.assertEqual(mailing.reply_to_mode, 'update')
        self.assertFalse(mailing.reply_to)

    @users('user_marketing')
    def test_mailing_computed_fields_default(self):
        mailing = self.env['mailing.mailing'].with_context(
            default_mailing_domain=repr([('email', 'ilike', 'test.example.com')])
        ).create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('email', 'ilike', 'test.example.com')])

    @users('user_marketing')
    def test_mailing_computed_fields_form(self):
        mailing_form = Form(self.env['mailing.mailing'].with_context(
            default_mailing_domain="[('email', 'ilike', 'test.example.com')]",
            default_mailing_model_id=self.env['ir.model']._get('res.partner').id,
        ))
        self.assertEqual(
            literal_eval(mailing_form.mailing_domain),
            [('email', 'ilike', 'test.example.com')],
        )
        self.assertEqual(mailing_form.mailing_model_real, 'res.partner')


class TestMassMailFeatures(MassMailCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailFeatures, cls).setUpClass()
        cls._create_mailing_list()

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_cron_trigger(self):
        """ Technical test to ensure the cron is triggered at the correct
        time """

        cron_id = self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').id
        partner = self.env['res.partner'].create({
            'name': 'Jean-Alphonce',
            'email': 'jeanalph@example.com',
        })
        common_mailing_values = {
            'name': 'Knock knock',
            'subject': "Who's there?",
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_domain': [('id', '=', partner.id)],
            'body_html': 'The marketing mailing test.',
            'schedule_type': 'scheduled',
        }

        now = datetime(2021, 2, 5, 16, 43, 20)
        then = datetime(2021, 2, 7, 12, 0, 0)

        with freeze_time(now):
            for (test, truth) in [(False, now), (then, then)]:
                with self.subTest(schedule_date=test):
                    with self.capture_triggers(cron_id) as capt:
                        mailing = self.env['mailing.mailing'].create({
                            **common_mailing_values,
                            'schedule_date': test,
                        })
                        mailing.action_put_in_queue()
                    capt.records.ensure_one()
                    self.assertLessEqual(capt.records.call_at, truth)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_deletion(self):
        """ Test deletion in various use case, depending on reply-to """
        # 1- Keep archives and reply-to set to 'answer = new thread'
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestSource',
            'subject': 'TestDeletion',
            'body_html': "<div>Hello {object.name}</div>",
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [(6, 0, self.mailing_list_1.ids)],
            'keep_archives': True,
            'reply_to_mode': 'new',
            'reply_to': self.email_reply_to,
        })
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        self.assertEqual(len(self._mails), 3)
        self.assertEqual(len(self._new_mails.exists()), 3)
        self.assertEqual(len(self.mailing_list_1.contact_ids.message_ids), 3)

        # 2- Keep archives and reply-to set to 'answer = update thread'
        self.mailing_list_1.contact_ids.message_ids.unlink()
        mailing = mailing.copy()
        mailing.write({
            'reply_to_mode': 'update',
        })
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        self.assertEqual(len(self._mails), 3)
        self.assertEqual(len(self._new_mails.exists()), 3)
        self.assertEqual(len(self.mailing_list_1.contact_ids.message_ids), 3)

        # 3- Remove archives and reply-to set to 'answer = new thread'
        self.mailing_list_1.contact_ids.message_ids.unlink()
        mailing = mailing.copy()
        mailing.write({
            'keep_archives': False,
            'reply_to_mode': 'new',
            'reply_to': self.email_reply_to,
        })
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        self.assertEqual(len(self._mails), 3)
        self.assertEqual(len(self._new_mails.exists()), 0)
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        # 4- Remove archives and reply-to set to 'answer = update thread'
        # Imply keeping mail.message for gateway reply)
        self.mailing_list_1.contact_ids.message_ids.unlink()
        mailing = mailing.copy()
        mailing.write({
            'keep_archives': False,
            'reply_to_mode': 'update',
        })
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        self.assertEqual(len(self._mails), 3)
        self.assertEqual(len(self._new_mails.exists()), 0)
        self.assertEqual(len(self.mailing_list_1.contact_ids.message_ids), 3)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_on_res_partner(self):
        """ Test mailing on res.partner model: ensure default recipients are
        correctly computed """
        partner_a = self.env['res.partner'].create({
            'name': 'test email 1',
            'email': 'test1@example.com',
        })
        partner_b = self.env['res.partner'].create({
            'name': 'test email 2',
            'email': 'test2@example.com',
        })
        self.env['mail.blacklist'].create({'email': 'Test2@example.com',})

        mailing = self.env['mailing.mailing'].create({
            'name': 'One',
            'subject': 'One',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_domain': [('id', 'in', (partner_a | partner_b).ids)],
            'body_html': 'This is mass mail marketing demo'
        })
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'partner': partner_a},
             {'partner': partner_b, 'trace_status': 'cancel', 'failure_type': 'mail_bl'}],
            mailing, partner_a + partner_b, check_mail=True
        )

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_shortener(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestSource',
            'subject': 'TestShortener',
            'body_html': """<div>
Hi,
<t t-set="url" t-value="'www.odoo.com'"/>
<t t-set="httpurl" t-value="'https://www.odoo.eu'"/>
Website0: <a id="url0" t-attf-href="https://www.odoo.tz/my/{{object.name}}">https://www.odoo.tz/my/<t t-esc="object.name"/></a>
Website1: <a id="url1" href="https://www.odoo.be">https://www.odoo.be</a>
Website2: <a id="url2" t-attf-href="https://{{url}}">https://<t t-esc="url"/></a>
Website3: <a id="url3" t-att-href="httpurl"><t t-esc="httpurl"/></a>
External1: <a id="url4" href="https://www.example.com/foo/bar?baz=qux">Youpie</a>
Email: <a id="url5" href="mailto:test@odoo.com">test@odoo.com</a></div>""",
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'reply_to_mode': 'new',
            'reply_to': self.email_reply_to,
            'contact_list_ids': [(6, 0, self.mailing_list_1.ids)],
            'keep_archives': True,
        })

        mailing.action_put_in_queue()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'fleurus@example.com'},
             {'email': 'gorramts@example.com'},
             {'email': 'ybrant@example.com'}],
            mailing, self.mailing_list_1.contact_ids, check_mail=True
        )

        for contact in self.mailing_list_1.contact_ids:
            new_mail = self._find_mail_mail_wrecord(contact)
            for link_info in [('url0', 'https://www.odoo.tz/my/%s' % contact.name, True),
                              ('url1', 'https://www.odoo.be', True),
                              ('url2', 'https://www.odoo.com', True),
                              ('url3', 'https://www.odoo.eu', True),
                              ('url4', 'https://www.example.com/foo/bar?baz=qux', True),
                              ('url5', 'mailto:test@odoo.com', False)]:
                # TDE FIXME: why going to mail message id ? mail.body_html seems to fail, check
                link_params = {'utm_medium': 'Email', 'utm_source': mailing.name}
                if link_info[0] == 'url4':
                    link_params['baz'] = 'qux'
                self.assertLinkShortenedHtml(
                    new_mail.mail_message_id.body,
                    link_info,
                    link_params=link_params,
                )

class TestMailingScheduleDateWizard(MassMailCommon):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_schedule_date(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'mailing',
            'subject': 'some subject'
        })
        # create a schedule date wizard
        wizard_form = Form(
            self.env['mailing.mailing.schedule.date'].with_context(default_mass_mailing_id=mailing.id))

        # set a schedule date
        wizard_form.schedule_date = datetime(2021, 4, 30, 9, 0)
        wizard = wizard_form.save()
        wizard.action_schedule_date()

        # assert that the schedule_date and schedule_type fields are correct and that the mailing is put in queue
        self.assertEqual(mailing.schedule_date, datetime(2021, 4, 30, 9, 0))
        self.assertEqual(mailing.schedule_type, 'scheduled')
        self.assertEqual(mailing.state, 'in_queue')
