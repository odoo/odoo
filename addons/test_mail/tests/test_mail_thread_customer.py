# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import formataddr, mute_logger


@tagged('mail_thread_customer')
class TestMailThreadCustomer(TestMailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailThreadCustomer, cls).setUpClass()

        cls.email_from = 'Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>'
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'test.customer',
            'alias_user_id': False,
            'alias_model_id': cls.env['ir.model']._get('mail.test.customer').id,
            'alias_contact': 'everyone'})

        cls.partner_from = '"FormattedContact" <%s>' % cls.partner_1.email_normalized
        cls._init_mail_gateway()

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_gateway_new(self):
        record = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.customer@test.com',
            subject='CustomerThread',
            cc='cc1@example.com, cc2@example.com',
            target_model='mail.test.customer')
        self.assertEqual(record.name, 'CustomerThread')
        self.assertEqual(record.email_from, formataddr(('Sylvie Lelitre', 'test.sylvie.lelitre@agrolait.com')))
        self.assertEqual(record.customer_id, self.env['res.partner'])
        self.assertEqual(record.user_id, self.env['res.users'])
        self.assertEqual(record.message_partner_ids, self.env['res.partner'])

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_gateway_new_customer(self):
        record = self.format_and_process(
            MAIL_TEMPLATE, self.partner_from, 'test.customer@test.com',
            subject='CustomerThread',
            cc='cc1@example.com, cc2@example.com',
            target_model='mail.test.customer')
        self.assertEqual(record.name, 'CustomerThread')
        self.assertEqual(record.email_from, self.partner_from)
        self.assertEqual(record.customer_id, self.partner_1)
        self.assertEqual(record.user_id, self.env['res.users'])
        self.assertEqual(record.message_partner_ids, self.partner_1)
