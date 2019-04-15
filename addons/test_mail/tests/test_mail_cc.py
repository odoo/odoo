# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests import common
from odoo.tests import tagged
from odoo.tools import mute_logger, email_split_and_format
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE


@tagged('mail_thread_cc')
class TestMailCc(common.BaseFunctionalTest, common.MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMailCc, cls).setUpClass()

        cls.email_from = 'Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>'
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'cc_record',
            'alias_user_id': False,
            'alias_model_id': cls.env['ir.model']._get('mail.test.cc').id,
            'alias_contact': 'everyone'})

        cls.env['ir.config_parameter'].set_param('mail.bounce.alias', 'bounce.test')
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', 'test.com')
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', 'catchall.test')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_new(self):
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'cc_record@test.com',
                                         cc='cc1@example.com, cc2@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['cc1@example.com', 'cc2@example.com'])

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_update_with_old(self):
        record = self.env['mail.test.cc'].create({'email_cc': 'cc1 <cc1@example.com>, cc2@example.com'})
        self.alias.write({'alias_force_thread_id': record.id})

        self.format_and_process(MAIL_TEMPLATE, self.email_from, 'cc_record@test.com',
                                cc='cc2 <cc2@example.com>, cc3@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['cc1 <cc1@example.com>', 'cc2@example.com', 'cc3@example.com'], 'new cc should have been added on record (unique)')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_update_no_old(self):
        record = self.env['mail.test.cc'].create({})
        self.alias.write({'alias_force_thread_id': record.id})

        self.format_and_process(MAIL_TEMPLATE, self.email_from, 'cc_record@test.com',
                                cc='cc2 <cc2@example.com>, cc3@example.com', target_model='mail.test.cc')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['cc2 <cc2@example.com>', 'cc3@example.com'], 'new cc should have been added on record (unique)')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_cc_recipient_suggestion(self):
        record = self.env['mail.test.cc'].create({'email_cc': 'cc1@example.com, cc2@example.com, cc3 <cc3@example.com>'})
        suggestions = record.message_get_suggested_recipients()[record.id]
        self.assertEqual(sorted(suggestions), [
            (False, 'cc1@example.com', 'CC Email'),
            (False, 'cc2@example.com', 'CC Email'),
            (False, 'cc3 <cc3@example.com>', 'CC Email')
        ], 'cc should be in suggestions')
