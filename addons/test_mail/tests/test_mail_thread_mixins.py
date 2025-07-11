# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions, tools
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tests.mail_tracking_duration_mixin_case import MailTrackingDurationMixinCase
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('mail_thread', 'mail_track', 'is_query_count')
class TestMailTrackingDurationMixin(MailTrackingDurationMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('mail.test.mail.tracking.duration')

    def test_mail_tracking_duration(self):
        self._test_record_duration_tracking()

    def test_mail_tracking_duration_batch(self):
        self._test_record_duration_tracking_batch()

    def test_queries_batch_mail_tracking_duration(self):
        self._test_queries_batch_duration_tracking()


@tagged('mail_thread', 'mail_blacklist')
class TestMailThread(MailCommon, TestRecipients):

    @mute_logger('odoo.models.unlink')
    def test_blacklist_mixin_email_normalized(self):
        """ Test email_normalized and is_blacklisted fields behavior, notably
        when dealing with encapsulated email fields and multi-email input. """
        base_email = 'test.email@test.example.com'

        # test data: source email, expected email normalized
        valid_pairs = [
            (base_email, base_email),
            (tools.formataddr(('Another Name', base_email)), base_email),
            (f'Name That Should Be Escaped <{base_email}>', base_email),
            ('test.😊@example.com', 'test.😊@example.com'),
            ('"Name 😊" <test.😊@example.com>', 'test.😊@example.com'),
        ]
        void_pairs = [(False, False),
                      ('', False),
                      (' ', False)]
        multi_pairs = [
            (f'{base_email}, other.email@test.example.com',
             base_email),  # multi supports first found
            (f'{tools.formataddr(("Another Name", base_email))}, other.email@test.example.com',
             base_email),  # multi supports first found
        ]
        for email_from, exp_email_normalized in valid_pairs + void_pairs + multi_pairs:
            with self.subTest(email_from=email_from, exp_email_normalized=exp_email_normalized):
                new_record = self.env['mail.test.gateway'].create({
                    'email_from': email_from,
                    'name': 'BL Test',
                })
                self.assertEqual(new_record.email_normalized, exp_email_normalized)
                self.assertFalse(new_record.is_blacklisted)

                # blacklist email should fail as void
                if email_from in [pair[0] for pair in void_pairs]:
                    with self.assertRaises(exceptions.UserError):
                        bl_record = self.env['mail.blacklist']._add(email_from)
                # blacklist email currently fails but could not
                elif email_from in [pair[0] for pair in multi_pairs]:
                    with self.assertRaises(exceptions.UserError):
                        bl_record = self.env['mail.blacklist']._add(email_from)
                # blacklist email ok
                else:
                    bl_record = self.env['mail.blacklist']._add(email_from)
                    self.assertEqual(bl_record.email, exp_email_normalized)
                    new_record.invalidate_recordset(fnames=['is_blacklisted'])
                    self.assertTrue(new_record.is_blacklisted)

                bl_record.unlink()


@tagged('mail_thread', 'mail_thread_cc')
class TestMailThreadCC(MailCommon):

    @users("employee")
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_suggested_recipients_mail_cc(self):
        """ MailThreadCC mixin adds its own suggested recipients management
        coming from CC (carbon copy) management. """
        record = self.env['mail.test.cc'].create({
            'email_cc': 'cc1@example.com, cc2@example.com, cc3 <cc3@example.com>',
        })
        suggestions = record._message_get_suggested_recipients()
        self.assertItemsEqual(
            suggestions,
            [
                {
                    'lang': None,
                    'reason': 'CC Email',
                    'name': 'cc1@example.com',
                    'email': 'cc1@example.com',
                    'create_values': {},
                }, {
                    'lang': None,
                    'reason': 'CC Email',
                    'name': 'cc2@example.com',
                    'email': 'cc2@example.com',
                    'create_values': {},
                }, {
                    'lang': None,
                    'reason': 'CC Email',
                    'name': '"cc3" <cc3@example.com>',
                    'email': '"cc3" <cc3@example.com>',
                    'create_values': {},
                },
            ],
            'cc should be in suggestions',
        )
