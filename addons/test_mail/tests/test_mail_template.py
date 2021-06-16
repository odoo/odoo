# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_template')
class TestMailTemplate(TestMailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailTemplate, cls).setUpClass()
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

        # activate translations
        cls.env['res.lang']._activate_lang('es_ES')
        cls.env.ref('base.module_base')._update_translations(['es_ES'])

        # create a complete test template
        cls.test_template = cls._create_template('mail.test.lang', {
            'attachment_ids': [(0, 0, cls._attachments[0]), (0, 0, cls._attachments[1])],
            'body_html': '<p>English Body for <t t-out="object.name"/></p>',
            'lang': '{{ object.customer_id.lang or object.lang }}',
            'email_to': '%s, %s' % (cls.email_1, cls.email_2),
            'email_cc': '%s' % cls.email_3,
            'partner_to': '%s,%s' % (cls.partner_2.id, cls.user_admin.partner_id.id),
            'subject': 'English for {{ object.name }}',
        })

        # Make sure Spanish translations have not been altered
        description_translations = cls.env['ir.translation'].search([
            ('module', '=', 'test_mail'),
            ('src', '=', cls.test_record._description),
            ('lang', '=', 'es_ES')
        ])
        if description_translations:
            description_translations.update({'value': 'Spanish description'})
        else:
            description_translations.create({
                'type': 'model',
                'name': 'ir.model,name',
                'module': 'test_mail',
                'lang': 'es_ES',
                'res_id': cls.env['ir.model']._get_id('mail.test.lang'),
                'src': cls.test_record._description,
                'value': 'Spanish description',
                'state': 'translated',
            })

        cls.env['ir.translation'].create({
            'type': 'model',
            'name': 'mail.template,subject',
            'module': 'mail',
            'lang': 'es_ES',
            'res_id': cls.test_template.id,
            'value': 'Spanish for {{ object.name }}',
            'state': 'translated',
        })
        cls.env['ir.translation'].create({
            'type': 'model',
            'name': 'mail.template,body_html',
            'module': 'mail',
            'lang': 'es_ES',
            'res_id': cls.test_template.id,
            'value': '<p>Spanish Body for <t t-out="object.name" /></p>',
            'state': 'translated',
        })
        view = cls.env['ir.ui.view'].create({
            'name': 'test_layout',
            'key': 'test_layout',
            'type': 'qweb',
            'arch_db': '<body><t t-out="message.body"/> English Layout <t t-esc="model_description"/></body>'
        })
        cls.env['ir.model.data'].create({
            'name': 'test_layout',
            'module': 'test_mail',
            'model': 'ir.ui.view',
            'res_id': view.id
        })
        cls.env['ir.translation'].create({
            'type': 'model_terms',
            'name': 'ir.ui.view,arch_db',
            'module': 'test_mail',
            'lang': 'es_ES',
            'res_id': view.id,
            'src': 'English Layout',
            'value': 'Spanish Layout',
            'state': 'translated',
        })

        # admin should receive emails
        cls.user_admin.write({'notification_type': 'email'})
        # Force the attachments of the template to be in the natural order.
        cls.test_template.invalidate_cache(['attachment_ids'], ids=cls.test_template.ids)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_send_email(self):
        mail_id = self.test_template.send_mail(self.test_record.id)
        mail = self.env['mail.mail'].sudo().browse(mail_id)
        self.assertEqual(mail.email_cc, self.test_template.email_cc)
        self.assertEqual(mail.email_to, self.test_template.email_to)
        self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)
        self.assertEqual(mail.subject, 'English for %s' % self.test_record.name)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_translation_lang(self):
        test_record = self.env['mail.test.lang'].browse(self.test_record.ids)
        test_record.write({
            'lang': 'es_ES',
        })
        test_template = self.env['mail.template'].browse(self.test_template.ids)

        mail_id = test_template.send_mail(test_record.id, notif_layout='test_mail.test_layout')
        mail = self.env['mail.mail'].sudo().browse(mail_id)
        self.assertEqual(mail.body_html,
                         '<body><p>Spanish Body for %s</p> Spanish Layout Spanish description</body>' % self.test_record.name)
        self.assertEqual(mail.subject, 'Spanish for %s' % self.test_record.name)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_translation_partner_lang(self):
        test_record = self.env['mail.test.lang'].browse(self.test_record.ids)
        customer = self.env['res.partner'].create({
            'email': 'robert.carlos@test.example.com',
            'lang': 'es_ES',
            'name': 'Roberto Carlos',
            })
        test_record.write({
            'customer_id': customer.id,
        })
        test_template = self.env['mail.template'].browse(self.test_template.ids)

        mail_id = test_template.send_mail(test_record.id, notif_layout='test_mail.test_layout')
        mail = self.env['mail.mail'].sudo().browse(mail_id)
        self.assertEqual(mail.body_html,
                         '<body><p>Spanish Body for %s</p> Spanish Layout Spanish description</body>' % self.test_record.name)
        self.assertEqual(mail.subject, 'Spanish for %s' % self.test_record.name)

    def test_template_add_context_action(self):
        self.test_template.create_action()

        # check template act_window has been updated
        self.assertTrue(bool(self.test_template.ref_ir_act_window))

        # check those records
        action = self.test_template.ref_ir_act_window
        self.assertEqual(action.name, 'Send Mail (%s)' % self.test_template.name)
        self.assertEqual(action.binding_model_id.model, 'mail.test.lang')

    # def test_template_scheduled_date(self):
    #     from unittest.mock import patch

    #     self.email_template_in_2_days = self.email_template.copy()

    #     with patch('odoo.addons.mail.tests.test_mail_template.datetime', wraps=datetime) as mock_datetime:
    #         mock_datetime.now.return_value = datetime(2017, 11, 15, 11, 30, 28)
    #         mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

    #         self.email_template_in_2_days.write({
    #             'scheduled_date': "{{ (datetime.datetime.now() + relativedelta(days=2)).strftime('%s') }}" % DEFAULT_SERVER_DATETIME_FORMAT,
    #         })

    #         mail_now_id = self.email_template.send_mail(self.test_record.id)
    #         mail_in_2_days_id = self.email_template_in_2_days.send_mail(self.test_record.id)

    #         mail_now = self.env['mail.mail'].browse(mail_now_id)
    #         mail_in_2_days = self.env['mail.mail'].browse(mail_in_2_days_id)

    #         # mail preparation
    #         self.assertEqual(mail_now.exists() | mail_in_2_days.exists(), mail_now | mail_in_2_days)
    #         self.assertEqual(bool(mail_now.scheduled_date), False)
    #         self.assertEqual(mail_now.state, 'outgoing')
    #         self.assertEqual(mail_in_2_days.state, 'outgoing')
    #         scheduled_date = datetime.strptime(mail_in_2_days.scheduled_date, DEFAULT_SERVER_DATETIME_FORMAT)
    #         date_in_2_days = datetime.now() + timedelta(days = 2)
    #         self.assertEqual(scheduled_date, date_in_2_days)
    #         # self.assertEqual(scheduled_date.month, date_in_2_days.month)
    #         # self.assertEqual(scheduled_date.year, date_in_2_days.year)

    #         # Launch the scheduler on the first mail, it should be reported in self.mails
    #         # and the mail_mail is now deleted
    #         self.env['mail.mail'].process_email_queue()
    #         self.assertEqual(mail_now.exists() | mail_in_2_days.exists(), mail_in_2_days)

    #         # Launch the scheduler on the first mail, it's still in 'outgoing' state
    #         self.env['mail.mail'].process_email_queue(ids=[mail_in_2_days.id])
    #         self.assertEqual(mail_in_2_days.state, 'outgoing')
    #         self.assertEqual(mail_now.exists() | mail_in_2_days.exists(), mail_in_2_days)
