# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from datetime import datetime
from freezegun import freeze_time
from psycopg2 import IntegrityError
from unittest.mock import patch

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.exceptions import ValidationError
from odoo.sql_db import Cursor
from odoo.tests.common import users, Form
from odoo.tools import mute_logger


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
    def test_mailing_computed_fields_domain_w_filter(self):
        """ Test domain update, involving mailing.filters added in 15.1. """
        # Create on res.partner, with default values for computed fields
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        # default for partner: remove blacklisted
        self.assertEqual(literal_eval(mailing.mailing_domain), [('is_blacklisted', '=', False)])

        # prepare initial data
        filter_1, filter_2, filter_3 = self.env['mailing.filter'].create([
            {'name': 'General channel',
             'mailing_domain' : [('name', '=', 'general')],
             'mailing_model_id': self.env['ir.model']._get('mail.channel').id,
            },
            {'name': 'LLN City',
             'mailing_domain' : [('city', 'ilike', 'LLN')],
             'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            },
            {'name': 'Email based',
             'mailing_domain' : [('email', 'ilike', 'info@odoo.com')],
             'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            }
        ])

        # check that adding mailing_filter_id updates domain correctly
        mailing.mailing_filter_id = filter_2
        self.assertEqual(literal_eval(mailing.mailing_domain), literal_eval(filter_2.mailing_domain))

        # cannot set a filter linked to another model
        with self.assertRaises(ValidationError):
            mailing.mailing_filter_id = filter_1

        # resetting model should reset domain, even if filter was chosen previously
        mailing.mailing_model_id = self.env['ir.model']._get('mail.channel').id
        self.assertEqual(literal_eval(mailing.mailing_domain), [])

        # changing the filter should update the mailing domain correctly
        mailing.mailing_filter_id = filter_1
        self.assertEqual(literal_eval(mailing.mailing_domain), literal_eval(filter_1.mailing_domain))

        # changing the domain should not empty the mailing_filter_id
        mailing.mailing_domain = "[('email', 'ilike', 'info_be@odoo.com')]"
        self.assertEqual(mailing.mailing_filter_id, filter_1, "Filter should not be unset even if domain is changed")

        # deleting the filter record should not delete the domain on mailing
        mailing.mailing_model_id = self.env['ir.model']._get('res.partner').id
        mailing.mailing_filter_id = filter_3
        filter_3_domain = filter_3.mailing_domain
        self.assertEqual(literal_eval(mailing.mailing_domain), literal_eval(filter_3_domain))
        filter_3.unlink()  # delete the filter record
        self.assertFalse(mailing.mailing_filter_id, "Should unset filter if it is deleted")
        self.assertEqual(literal_eval(mailing.mailing_domain), literal_eval(filter_3_domain), "Should still have the same domain")

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

    @mute_logger('odoo.sql_db')
    @users('user_marketing')
    def test_mailing_trace_values(self):
        recipient = self.partner_employee

        # both void and 0 are invalid, document should have an id != 0
        with self.assertRaises(IntegrityError):
            self.env['mailing.trace'].create({
                'model': recipient._name,
            })
        with self.assertRaises(IntegrityError):
            self.env['mailing.trace'].create({
                'model': recipient._name,
                'res_id': 0,
            })
        with self.assertRaises(IntegrityError):
            self.env['mailing.trace'].create({
                'res_id': 3,
            })

        activity = self.env['mailing.trace'].create({
            'model': recipient._name,
            'res_id': recipient.id,
        })
        with self.assertRaises(IntegrityError):
            activity.write({'model': False})
            self.env.flush_all()
        with self.assertRaises(IntegrityError):
            activity.write({'res_id': False})
            self.env.flush_all()
        with self.assertRaises(IntegrityError):
            activity.write({'res_id': 0})
            self.env.flush_all()

    @freeze_time('2022-01-02')
    @patch.object(Cursor, 'now', lambda *args, **kwargs: datetime(2022, 1, 2))
    @users('user_marketing')
    def test_mailing_unique_name(self):
        """Test that the names are generated and unique for each mailing.

        If the name is missing, it's generated from the subject. Then we should ensure
        that this generated name is unique.
        """
        mailing_0 = self.env['mailing.mailing'].create({'subject': 'First subject'})

        mailing_1, mailing_2, mailing_3, mailing_4, mailing_5, mailing_6 = self.env['mailing.mailing'].create([{
            'subject': 'First subject',
        }, {
            'subject': 'First subject',
        }, {
            'subject': 'First subject',
            'source_id': self.env['utm.source'].create({'name': 'Custom Source'}).id,
        }, {
            'subject': 'First subject',
            'name': 'Mailing',
        }, {
            'subject': 'Second subject',
            'name': 'Mailing',
        }, {
            'subject': 'Second subject',
        }])

        self.assertEqual(mailing_0.name, 'First subject (Mass Mailing created on 2022-01-02)')
        self.assertEqual(mailing_1.name, 'First subject (Mass Mailing created on 2022-01-02) [2]')
        self.assertEqual(mailing_2.name, 'First subject (Mass Mailing created on 2022-01-02) [3]')
        self.assertEqual(mailing_3.name, 'Custom Source')
        self.assertEqual(mailing_4.name, 'Mailing')
        self.assertEqual(mailing_5.name, 'Mailing [2]')
        self.assertEqual(mailing_6.name, 'Second subject (Mass Mailing created on 2022-01-02)')

        mailing_0.subject = 'First subject'
        self.assertEqual(mailing_0.name, 'First subject (Mass Mailing created on 2022-01-02) [4]',
            msg='The name must have been re-generated')

        mailing_0.name = 'Second subject (Mass Mailing created on 2022-01-02)'
        self.assertEqual(mailing_0.name, 'Second subject (Mass Mailing created on 2022-01-02) [2]',
            msg='The name must be unique')


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
