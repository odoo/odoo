# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.addons.test_mail.tests.common import BaseFunctionalTest, MockEmails, TestRecipients
from odoo.tools import mute_logger


class TestMailTemplate(BaseFunctionalTest, MockEmails, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailTemplate, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

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
        cls._create_template('mail.test.simple', {
            'attachment_ids': [(0, 0, cls._attachments[0]), (0, 0, cls._attachments[1])],
            'partner_to': '%s,%s' % (cls.partner_2.id, cls.user_admin.partner_id.id),
            'email_to': '%s, %s' % (cls.email_1, cls.email_2),
            'email_cc': '%s' % cls.email_3,
        })

        # admin should receive emails
        cls.user_admin.write({'notification_type': 'email'})
        # Force the attachments of the template to be in the natural order.
        cls.email_template.invalidate_cache(['attachment_ids'], ids=cls.email_template.ids)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_send_email(self):
        mail_id = self.email_template.send_mail(self.test_record.id)
        mail = self.env['mail.mail'].browse(mail_id)
        self.assertEqual(mail.subject, 'About %s' % self.test_record.name)
        self.assertEqual(mail.email_to, self.email_template.email_to)
        self.assertEqual(mail.email_cc, self.email_template.email_cc)
        self.assertEqual(mail.recipient_ids, self.partner_2 | self.user_admin.partner_id)

    def test_template_add_context_action(self):
        self.email_template.create_action()

        # check template act_window has been updated
        self.assertTrue(bool(self.email_template.ref_ir_act_window))

        # check those records
        action = self.email_template.ref_ir_act_window
        self.assertEqual(action.name, 'Send Mail (%s)' % self.email_template.name)
        self.assertEqual(action.binding_model_id.model, 'mail.test.simple')

    def test_template_send_email_translations_with_notif_layout(self):
        self.env['res.lang'].load_lang('fr_FR')
        self.test_record = self.env['mail.test.full'].with_context(self._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
            'customer_id': self.partner_2.id,
        })
        self._create_template('mail.test.full', {
            'partner_to': '%s' % self.partner_2.id,
            'email_to': '%s' % self.partner_2.email,
            'lang': '${object.customer_id.lang}',
        })
        ARCH = '<template id="test_notification_template">%s</template>'
        TEXT_EN = "Notification Template"
        TEXT_FR = u"Template de notification"
        view = self.env['ir.ui.view']._load_records([dict(xml_id='test_mail.test_notification_template', values={
            'name': 'test_notification_template',
            'arch': ARCH % TEXT_EN,
            'inherit_id': False,
            'type': 'qweb',
        })])
        self.env['ir.translation'].create({
            'type': 'model_terms',
            'name': 'ir.ui.view,arch_db',
            'res_id': view.id,
            'lang': 'fr_FR',
            'src': TEXT_EN,
            'value': TEXT_FR,
        })
        self.partner_2.lang = 'fr_FR'

        mail_id = self.email_template.send_mail(self.test_record.id, False, False, None, 'test_mail.test_notification_template')
        mail = self.env['mail.mail'].browse(mail_id)
        self.assertEqual(mail.body_html, ARCH % TEXT_FR)

    # def test_template_scheduled_date(self):
    #     from unittest.mock import patch

    #     self.email_template_in_2_days = self.email_template.copy()

    #     with patch('odoo.addons.mail.tests.test_mail_template.datetime', wraps=datetime) as mock_datetime:
    #         mock_datetime.now.return_value = datetime(2017, 11, 15, 11, 30, 28)
    #         mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

    #         self.email_template_in_2_days.write({
    #             'scheduled_date': "${(datetime.datetime.now() + relativedelta(days=2)).strftime('%s')}" % DEFAULT_SERVER_DATETIME_FORMAT,
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
