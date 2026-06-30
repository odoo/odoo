# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import exceptions, tools
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tests.common_tracking import MailTrackingDurationMixinCase
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('mail_thread', 'mail_track', 'is_query_count')
class TestMailTrackingDurationMixin(MailTrackingDurationMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('mail.test.track.duration.mixin')

    def test_mail_tracking_duration(self):
        self._test_record_duration_tracking()

    def test_mail_tracking_duration_batch(self):
        self._test_record_duration_tracking_batch()

    def test_queries_batch_mail_tracking_duration(self):
        self._test_queries_batch_duration_tracking()


@tagged('mail_thread', 'mail_track')
class TestMailThreadRottingMixin(MailTrackingDurationMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass('mail.test.rotting.resource')

        [cls.stage_new, cls.stage_qualification, cls.stage_finished] = cls.env['mail.test.rotting.stage'].create([
            {
                'name': 'stage_new',
                'rotting_threshold_days': 3,
            }, {
                'name': 'stage_qualification',
                'rotting_threshold_days': 5,
            }, {
                'name': 'stage_finished',
                'rotting_threshold_days': 1,
                'no_rot': True,
            },
        ])

    def test_resource_rotting(self):
        # create dates for the test
        jan1 = datetime(2025, 1, 1)
        jan5 = datetime(2025, 1, 5)
        jan7 = datetime(2025, 1, 7)
        jan12 = datetime(2025, 1, 12)
        jan28 = datetime(2025, 1, 28)

        # create resources for the test, created on jan 1
        with self.mock_datetime_and_now(jan1):
            items = [item1, item2, item3, item_done, item_won] = self.env['mail.test.rotting.resource'].create([
                {
                    'name': 'item1',
                    'stage_id': self.stage_new.id,
                }, {
                    'name': 'item2',
                    'stage_id': self.stage_qualification.id,
                }, {
                    'name': 'item3',
                    'stage_id': self.stage_new.id,
                }, {
                    'name': 'item_done',
                    'stage_id': self.stage_qualification.id,
                    'done': True,
                }, {
                    'name': 'item_wonStage',
                    'stage_id': self.stage_finished.id,
                },
            ])
            items.flush_recordset(['date_last_stage_update'])  # precalculate stage update()

        with self.mock_datetime_and_now(jan5):
            # need to invalidate on date change to ensure rotting computations
            items.invalidate_recordset(['is_rotting'])
            for item in [item1, item3]:
                self.assertTrue(
                    item.is_rotting,
                    'on jan 5: it\'s been four days, so only items in stage_new should be rotting',
                )
                self.assertEqual(item.rotting_days, 4)
            for item in [item2, item_done, item_won]:
                self.assertFalse(
                    item.is_rotting,
                    'on jan 5: it\'s been four days, so only items in stage_new should be rotting',
                )
                self.assertEqual(item.rotting_days, 0)

            item3.name = 'item3 edited'
            self.assertTrue(
                item3.is_rotting,
                'writing to an item doesn\'t affect its rotting status',
            )

        with self.mock_datetime_and_now(jan7):
            items.invalidate_recordset(['is_rotting'])
            self.assertTrue(
                item2.is_rotting,
                'on jan 7: items belonging to stage_qualification should be rotting, except if their state forbids it',
            )
            self.assertEqual(item2.rotting_days, 6)
            self.assertFalse(
                item_done.is_rotting,
                'item_done is marked as done, it should not be able to rot',
            )

            self.assertTrue(item1.is_rotting)
            item1.message_post(body='Message received', message_type='email')
            self.assertTrue(
                item1.is_rotting,
                'Receiving an email should not remove rotting',
            )

            item1.message_post(body='Message sent', message_type='email_outgoing')
            self.assertTrue(
                item1.is_rotting,
                'Nor should sending an email',
            )

            self.assertFalse(
                item_won.is_rotting,
                'Items in stage_finished cannot rot',
            )
            self.stage_finished.no_rot = False
            self.assertTrue(
                item_won.is_rotting,
                'However if the stage no longer disallows rotting, then all items in the stage may once more rot',
            )

            self.stage_finished.no_rot = True
            self.assertFalse(
                item_won.is_rotting,
                'Disallowing rotting once again should disable rotting once more',
            )

        with self.mock_datetime_and_now(jan12):
            items.invalidate_recordset(['rotting_days', 'is_rotting'])

            self.assertTrue(item3.is_rotting)
            self.stage_new.rotting_threshold_days = 40
            self.assertFalse(
                item3.is_rotting,
                'Changing the threshold should affect the status immediately)',
            )

            self.stage_new.rotting_threshold_days = 1

            item3.stage_id = self.stage_qualification
            self.assertFalse(
                item3.is_rotting,
                'Changing stages always removes rotting',
            )

            self.stage_qualification.rotting_threshold_days = 0
            self.assertFalse(
                item2.is_rotting,
                'Setting rotting_threshold_days at 0 on a stage immediately disables rotting for the stage',
            )

        with self.mock_datetime_and_now(jan28):
            items.invalidate_recordset(['rotting_days', 'is_rotting'])
            # After a significant amount of time has passed:
            self.assertTrue(
                item1.is_rotting,
                'Items that are not done or won are rotting',
            )
            for item in [item2, item3, item_done, item_won]:
                self.assertFalse(
                    item.is_rotting,
                    'Items that are not done, won, or in a disabled rotting stage are not rotting',
                )


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


@tagged('mail_thread', 'mail_thread_cc', 'mail_tools')
class TestMailThreadCC(MailCommon):

    @users("employee")
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_suggested_recipients_mail_cc(self):
        """ MailThreadCC mixin adds its own suggested recipients management
        coming from CC (carbon copy) management. """
        record = self.env['mail.test.cc'].create({
            'email_cc': 'cc1@example.com, cc2@example.com, cc3 <cc3@example.com>',
        })
        suggestions = record._message_get_suggested_recipients(no_create=True)
        expected_list = [
            {
                'name': '', 'email': 'cc1@example.com',
                'partner_id': False, 'create_values': {},
            }, {
                'name': '', 'email': 'cc2@example.com',
                'partner_id': False, 'create_values': {},
            }, {
                'name': 'cc3', 'email': 'cc3@example.com',
                'partner_id': False, 'create_values': {},
            }]
        self.assertEqual(len(suggestions), len(expected_list))
        for suggestion, expected in zip(suggestions, expected_list):
            self.assertDictEqual(suggestion, expected)
