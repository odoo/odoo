# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests import common
from odoo.tests import tagged
from odoo.tools import mute_logger, email_split_and_format
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE


@tagged('cc_test')
class TestMailResend(common.BaseFunctionalTest, common.MockEmails):

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_new(self):
        alias = self.env['mail.alias'].create({
            'alias_name': 'cc_record',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.cc').id,
            'alias_contact': 'everyone'})
        record = self.format_and_process(MAIL_TEMPLATE, target_model='mail.test.cc', to='cc_record@example.com',
                                         cc='cc1@example.com, cc2@example.com')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['cc1@example.com', 'cc2@example.com'], 'cc should contains exactly 2 cc')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_update_with_old(self):
        record = self.env['mail.test.cc'].create({'email_cc': 'cc1 <cc1@example.com>, cc2@example.com'})
        alias = self.env['mail.alias'].create({
            'alias_name': 'cc_record',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.cc').id,
            'alias_contact': 'everyone',
            'alias_force_thread_id': record.id})

        self.format_and_process(MAIL_TEMPLATE, subject='Re: Frogs', target_model='mail.test.cc',
                                msg_id='1198923581.41972151344608186799.JavaMail.diff1@agrolait.com',
                                to='cc_record@example.com',
                                cc='cc2 <cc2@example.com>, cc3@example.com')
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ['cc1 <cc1@example.com>', 'cc2@example.com', 'cc3@example.com'], 'new cc should have been added on record (unique)')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_message_cc_update_no_old(self):
        record = self.env['mail.test.cc'].create({})
        alias = self.env['mail.alias'].create({
            'alias_name': 'cc_record',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mail.test.cc').id,
            'alias_contact': 'everyone',
            'alias_force_thread_id': record.id})
        self.format_and_process(MAIL_TEMPLATE, subject='Re: Frogs', target_model='mail.test.cc',
                                msg_id='1198923581.41972151344608186799.JavaMail.diff1@agrolait.com',
                                to='cc_record@example.com',
                                cc='cc2 <cc2@example.com>, cc3@example.com')
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
