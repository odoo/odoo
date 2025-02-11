# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.tests import tagged


@tagged('mail_management')
class TestMailManagement(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailManagement, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test'})
        cls._reset_mail_context(cls.test_record)
        cls.msg = cls.test_record.message_post(body='TEST BODY', author_id=cls.partner_employee.id)
        cls.notif_p1 = cls.env['mail.notification'].create({
            'author_id': cls.msg.author_id.id,
            'mail_message_id': cls.msg.id,
            'res_partner_id': cls.partner_1.id,
            'notification_type': 'email',
            'notification_status': 'exception',
            'failure_type': 'mail_smtp',
        })
        cls.notif_p2 = cls.env['mail.notification'].create({
            'author_id': cls.msg.author_id.id,
            'mail_message_id': cls.msg.id,
            'res_partner_id': cls.partner_2.id,
            'notification_type': 'email',
            'notification_status': 'bounce',
            'failure_type': 'unknown',
        })
        cls.partner_3 = cls.env['res.partner'].create({
            'name': 'Partner3',
            'email': 'partner3@example.com',
        })
        cls.notif_p3 = cls.env['mail.notification'].create({
            'author_id': cls.msg.author_id.id,
            'mail_message_id': cls.msg.id,
            'res_partner_id': cls.partner_3.id,
            'notification_type': 'email',
            'notification_status': 'sent',
            'failure_type': None,
        })

    def test_mail_notify_cancel(self):
        self._reset_bus()

        self.test_record.with_user(self.user_employee).notify_cancel_by_type('email')
        self.assertEqual((self.notif_p1 | self.notif_p2 | self.notif_p3).mapped('notification_status'),
                         ['canceled', 'canceled', 'sent'])

        self.assertMessageBusNotifications(self.msg)
