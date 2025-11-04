# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime

from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.tests import tagged, users, warmup
from odoo.tools import mute_logger, safe_eval


class TestMailTemplateCommon(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailTemplateCommon, cls).setUpClass()
        cls.test_record = cls.env['mail.test.lang'].with_context(cls._test_context).create({
            'email_from': 'ignasse@example.com',
            'name': 'Test',
        })

        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls._attachments = [{
            'name': 'first.txt',
            'datas': base64.b64encode(b'My first attachment'),
            'res_model': 'res.partner',
            'res_id': cls.user_admin.partner_id.id
        }, {
            'name': 'second.txt',
            'datas': base64.b64encode(b'My second attachment'),
            'res_model': 'res.partner',
            'res_id': cls.user_admin.partner_id.id
        }]

        cls.email_1 = 'test1@example.com'
        cls.email_2 = 'test2@example.com'
        cls.email_3 = cls.partner_1.email

        # create a complete test template
        cls.test_template = cls._create_template('mail.test.lang', {
            'attachment_ids': [(0, 0, cls._attachments[0]), (0, 0, cls._attachments[1])],
            'body_html': '<p>EnglishBody for <t t-out="object.name"/></p>',
            'lang': '{{ object.customer_id.lang or object.lang }}',
            'email_to': '%s, %s' % (cls.email_1, cls.email_2),
            'email_cc': '%s' % cls.email_3,
            'partner_to': '%s,%s' % (cls.partner_2.id, cls.user_admin.partner_id.id),
            'subject': 'EnglishSubject for {{ object.name }}',
        })

        # activate translations
        cls._activate_multi_lang(
            layout_arch_db='<body><t t-out="message.body"/> English Layout for <t t-esc="model_description"/></body>',
            test_record=cls.test_record, test_template=cls.test_template
        )

        # admin should receive emails
        cls.user_admin.write({'notification_type': 'email'})
        # Force the attachments of the template to be in the natural order.
        cls.test_template.invalidate_recordset(['attachment_ids'])


@tagged('mail_template')
class TestMailTemplate(TestMailTemplateCommon):

    def test_template_add_context_action(self):
        self.test_template.create_action()

        # check template act_window has been updated
        self.assertTrue(bool(self.test_template.ref_ir_act_window))

        # check those records
        action = self.test_template.ref_ir_act_window
        self.assertEqual(action.name, 'Send Mail (%s)' % self.test_template.name)
        self.assertEqual(action.binding_model_id.model, 'mail.test.lang')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_template_schedule_email(self):
        """ Test scheduling email sending from template. """
        now = datetime.datetime(2024, 4, 29, 10, 49, 59)
        test_template = self.test_template.with_env(self.env)

        # schedule the mail in 3 days -> patch safe_eval.datetime access
        safe_eval_orig = safe_eval.safe_eval

        def _safe_eval_hacked(*args, **kwargs):
            """ safe_eval wraps 'datetime' and freeze_time does not mock it;
            simplest solution found so far is to directly hack safe_eval just
            for this test """
            if args[0] == "datetime.datetime.now() + datetime.timedelta(days=3)":
                return now + datetime.timedelta(days=3)
            return safe_eval_orig(*args, **kwargs)

        # patch datetime and safe_eval.datetime, as otherwise using standard 'now'
        # might lead to errors due to test running right before minute switch it
        # sometimes ends at minute+1 and assert fails - see runbot-54946
        with patch.object(safe_eval, "safe_eval", autospec=True, side_effect=_safe_eval_hacked):
            test_template.scheduled_date = '{{datetime.datetime.now() + datetime.timedelta(days=3)}}'
            with freeze_time(now):
                mail_id = test_template.send_mail(self.test_record.id)
            mail = self.env['mail.mail'].sudo().browse(mail_id)
        self.assertEqual(
            mail.scheduled_date.replace(second=0, microsecond=0),
            (now + datetime.timedelta(days=3)).replace(second=0, microsecond=0),
        )
        self.assertEqual(mail.state, 'outgoing')

        # check a wrong format
        test_template.scheduled_date = '{{"test " * 5}}'
        with freeze_time(now):
            mail_id = test_template.send_mail(self.test_record.id)
        mail = self.env['mail.mail'].sudo().browse(mail_id)
        self.assertFalse(mail.scheduled_date)
        self.assertEqual(mail.state, 'outgoing')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_send_mail_body(self):
        """ Test that the body and body_html is set correctly in 'mail.mail'
        when sending an email from mail.template """
        mail_id = self.test_template.send_mail(self.test_record.id)
        mail = self.env['mail.mail'].sudo().browse(mail_id)
        body_result = '<p>EnglishBody for %s</p>' % self.test_record.name

        self.assertEqual(mail.body_html, body_result)
        self.assertEqual(mail.body, body_result)


@tagged('mail_template', 'multi_lang', 'mail_performance', 'post_install', '-at_install')
class TestMailTemplateLanguages(TestMailTemplateCommon):

    @classmethod
    def setUpClass(cls):
        """ Create lang-based records and templates, to test batch and performances
        with language involved. """
        super().setUpClass()

        # use test notification layout
        cls.test_template.write({
            'email_layout_xmlid': 'mail.test_layout',
        })

        # double record, one in each lang
        cls.test_records = cls.test_record + cls.env['mail.test.lang'].create({
            'email_from': 'ignasse.es@example.com',
            'lang': 'es_ES',
            'name': 'Test Record 2',
        })

        # pure batch, 100 records
        cls.test_records_batch, test_partners = cls._create_records_for_batch(
            'mail.test.lang', 100,
        )
        test_partners[:50].lang = 'es_ES'

        # have a template with dynamic templates to check impact
        cls.test_template_wreports = cls.test_template.copy({
            'email_layout_xmlid': 'mail.test_layout',
        })
        cls.test_reports = cls.env['ir.actions.report'].create([
            {
                'name': f'Test Report on {cls.test_record._name}',
                'model': cls.test_record._name,
                'print_report_name': "f'TestReport for {object.name}'",
                'report_type': 'qweb-pdf',
                'report_name': 'test_mail.mail_test_ticket_test_template',
            }, {
                'name': f'Test Report 2 on {cls.test_record._name}',
                'model': cls.test_record._name,
                'print_report_name': "f'TestReport2 for {object.name}'",
                'report_type': 'qweb-pdf',
                'report_name': 'test_mail.mail_test_ticket_test_template_2',
            }
        ])
        cls.test_template_wreports.report_template_ids = cls.test_reports

        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # warm up group access cache: 5 queries + 1 query per user
        self.user_employee.has_group('base.group_user')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @warmup
    def test_template_send_email(self):
        """ Test 'send_email' on template on a given record, used notably as
        contextual action. """
        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(13):
            mail_id = self.test_template.with_env(self.env).send_mail(self.test_record.id)
            mail = self.env['mail.mail'].sudo().browse(mail_id)

        self.assertEqual(sorted(mail.attachment_ids.mapped('name')), ['first.txt', 'second.txt'])
        self.assertEqual(mail.body_html,
                         f'<body><p>EnglishBody for {self.test_record.name}</p> English Layout for Lang Chatter Model</body>')
        self.assertEqual(mail.email_cc, self.test_template.email_cc)
        self.assertEqual(mail.email_to, self.test_template.email_to)
        self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)
        self.assertEqual(mail.subject, f'EnglishSubject for {self.test_record.name}')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @warmup
    def test_template_send_email_nolayout(self):
        """ Test without layout, just to check impact """
        self.test_template.email_layout_xmlid = False
        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(12):
            mail_id = self.test_template.with_env(self.env).send_mail(self.test_record.id)
            mail = self.env['mail.mail'].sudo().browse(mail_id)

        self.assertEqual(sorted(mail.attachment_ids.mapped('name')), ['first.txt', 'second.txt'])
        self.assertEqual(mail.body_html,
                         f'<p>EnglishBody for {self.test_record.name}</p>')
        self.assertEqual(mail.email_cc, self.test_template.email_cc)
        self.assertEqual(mail.email_to, self.test_template.email_to)
        self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)
        self.assertEqual(mail.subject, f'EnglishSubject for {self.test_record.name}')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @warmup
    def test_template_send_email_batch(self):
        """ Test 'send_email' on template in batch """
        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(25):
            template = self.test_template.with_env(self.env)
            mails_sudo = template.send_mail_batch(self.test_records_batch.ids)

        self.assertEqual(len(mails_sudo), 100)
        for idx, (mail, record) in enumerate(zip(mails_sudo, self.test_records_batch)):
            self.assertEqual(sorted(mail.attachment_ids.mapped('name')), ['first.txt', 'second.txt'])
            self.assertEqual(mail.attachment_ids.mapped("res_id"), [template.id] * 2)
            self.assertEqual(mail.attachment_ids.mapped("res_model"), [template._name] * 2)
            self.assertEqual(mail.email_cc, template.email_cc)
            self.assertEqual(mail.email_to, template.email_to)
            self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)
            if idx >= 50:
                self.assertEqual(mail.subject, f'EnglishSubject for {record.name}')
            else:
                self.assertEqual(mail.subject, f'SpanishSubject for {record.name}')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @warmup
    def test_template_send_email_wreport(self):
        """ Test 'send_email' on template on a given record, used notably as
        contextual action, with dynamic reports involved """
        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(23):
            mail_id = self.test_template_wreports.with_env(self.env).send_mail(self.test_record.id)
            mail = self.env['mail.mail'].sudo().browse(mail_id)

        self.assertEqual(
            sorted(mail.attachment_ids.mapped('name')),
            [f'TestReport for {self.test_record.name}.html', f'TestReport2 for {self.test_record.name}.html', 'first.txt', 'second.txt']
        )
        self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)
        self.assertEqual(mail.subject, f'EnglishSubject for {self.test_record.name}')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @warmup
    def test_template_send_email_wreport_batch(self):
        """ Test 'send_email' on template in batch with dynamic reports """
        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(234):
            template = self.test_template_wreports.with_env(self.env)
            mails_sudo = template.send_mail_batch(self.test_records_batch.ids)

        self.assertEqual(len(mails_sudo), 100)
        for idx, (mail, record) in enumerate(zip(mails_sudo, self.test_records_batch)):
            self.assertEqual(
                sorted(mail.attachment_ids.mapped('name')),
                [f'TestReport for {record.name}.html', f'TestReport2 for {record.name}.html', 'first.txt', 'second.txt']
            )
            self.assertEqual(
                sorted(mail.attachment_ids.mapped("res_id")),
                sorted([self.test_template_wreports.id] * 2 + [mail.mail_message_id.id] * 2),
                "Attachments: attachment_ids -> linked to template, attachments -> to mail.message"
            )
            self.assertEqual(
                sorted(mail.attachment_ids.mapped("res_model")),
                sorted([template._name] * 2 + ["mail.message"] * 2),
                "Attachments: attachment_ids -> linked to template, attachments -> to mail.message"
            )
            self.assertEqual(mail.email_cc, self.test_template.email_cc)
            self.assertEqual(mail.email_to, self.test_template.email_to)
            self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)
            if idx >= 50:
                self.assertEqual(mail.subject, f'EnglishSubject for {record.name}')
                self.assertEqual(mail.body_html,
                         f'<body><p>EnglishBody for {record.name}</p> English Layout for Lang Chatter Model</body>')
            else:
                self.assertEqual(mail.subject, f'SpanishSubject for {record.name}')
                self.assertEqual(mail.body_html,
                         f'<body><p>SpanishBody for {record.name}</p> Spanish Layout para Spanish Model Description</body>')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_send_email_wreport_batch_scalability(self):
        """ Test 'send_email' on template in batch, using configuration parameter
        for batch rendering. """
        for batch_size, exp_mail_create_count in [
            (False, 2),  # unset, default is 50
            (0, 2),  # 0: fallbacks on default
            (30, 4),  # 100 / 30 -> 4 iterations
        ]:
            with self.subTest(batch_size=batch_size):
                self.env['ir.config_parameter'].sudo().set_param(
                    "mail.batch_size", batch_size
                )
                with self.with_user(self.user_employee.login), \
                     self.mock_mail_gateway():
                    template = self.test_template_wreports.with_env(self.env)
                    mails_sudo = template.send_mail_batch(self.test_records_batch.ids)

                self.assertEqual(self.mail_mail_create_mocked.call_count, exp_mail_create_count)
                self.assertEqual(len(mails_sudo), 100)
                for idx, (mail, record) in enumerate(zip(mails_sudo, self.test_records_batch)):
                    self.assertEqual(
                        sorted(mail.attachment_ids.mapped('name')),
                        [f'TestReport for {record.name}.html', f'TestReport2 for {record.name}.html', 'first.txt', 'second.txt']
                    )
                    self.assertEqual(
                        sorted(mail.attachment_ids.mapped("res_id")),
                        sorted([self.test_template_wreports.id] * 2 + [mail.mail_message_id.id] * 2),
                        "Attachments: attachment_ids -> linked to template, attachments -> to mail.message"
                    )
                    self.assertEqual(
                        sorted(mail.attachment_ids.mapped("res_model")),
                        sorted([template._name] * 2 + ["mail.message"] * 2),
                        "Attachments: attachment_ids -> linked to template, attachments -> to mail.message"
                    )
                    self.assertEqual(mail.email_cc, self.test_template.email_cc)
                    self.assertEqual(mail.email_to, self.test_template.email_to)
                    self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)
                    if idx >= 50:
                        self.assertEqual(mail.subject, f'EnglishSubject for {record.name}')
                    else:
                        self.assertEqual(mail.subject, f'SpanishSubject for {record.name}')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_translation_lang(self):
        """ Test template rendering using lang defined directly on the record """
        test_record = self.test_record.with_env(self.env)
        test_record.write({
            'lang': 'es_ES',
        })
        test_template = self.test_template.with_env(self.env)

        mail_id = test_template.send_mail(test_record.id)
        mail = self.env['mail.mail'].sudo().browse(mail_id)
        self.assertEqual(mail.body_html,
                         f'<body><p>SpanishBody for {self.test_record.name}</p> Spanish Layout para Spanish Model Description</body>')
        self.assertEqual(mail.subject, f'SpanishSubject for {self.test_record.name}')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @warmup
    def test_template_translation_partner_lang(self):
        """ Test template rendering using lang defined on a sub-record aka
        'partner_id.lang' """
        test_records = self.env['mail.test.lang'].browse(self.test_records.ids)
        customers = self.env['res.partner'].create([
            {
                'email': 'roberto.carlos@test.example.com',
                'lang': 'es_ES',
                'name': 'Roberto Carlos',
            }, {
                'email': 'rob.charly@test.example.com',
                'lang': 'en_US',
                'name': 'Rob Charly',
            }
        ])
        test_records[0].write({'customer_id': customers[0].id})
        test_records[1].write({'customer_id': customers[1].id})

        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(18):
            template = self.test_template.with_env(self.env)
            mails_sudo = template.send_mail_batch(self.test_records.ids, email_layout_xmlid='mail.test_layout')

        self.assertEqual(mails_sudo[0].body_html,
                         f'<body><p>SpanishBody for {test_records[0].name}</p> Spanish Layout para Spanish Model Description</body>')
        self.assertEqual(mails_sudo[0].subject, f'SpanishSubject for {test_records[0].name}')
        self.assertEqual(mails_sudo[1].body_html,
                         f'<body><p>EnglishBody for {test_records[1].name}</p> English Layout for Lang Chatter Model</body>')
        self.assertEqual(mails_sudo[1].subject, f'EnglishSubject for {test_records[1].name}')
