# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo.addons.event.tests.common import EventCase
from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.social.tests.tools import mock_void_external_calls
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger


@tagged('event_mail', 'post_install', '-at_install')
class EventSocialCase(EventCase, MockEmail):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with mock_void_external_calls():
            cls.social_media = cls.env['social.media'].create({
                'name': 'Social Media',
            })
            cls.social_account = cls.env['social.account'].create({
                'media_id': cls.social_media.id,
                'name': 'Social Account 1',
            })

        cls.test_social_template = cls.env['social.post.template'].create({
            'account_ids': [(4, cls.social_account.id)],
            'message': 'Join the Python side of the force!',
        })

        cls.reference_now = datetime(2021, 3, 20, 14, 30, 15, 123456)
        cls.event_date_begin = datetime(2021, 3, 22, 8, 0, 0)
        cls.event_date_end = datetime(2021, 3, 24, 18, 0, 0)

        with cls.mock_datetime_and_now(cls, cls.reference_now):
            cls.test_event = cls.env['event.event'].create({
                'name': 'TestEvent',
                'date_begin': cls.event_date_begin,
                'date_end': cls.event_date_end,
                'event_mail_ids': [
                    (0, 0, {  # 1 days before event
                        'interval_nbr': 1,
                        'interval_unit': 'days',
                        'interval_type': 'before_event',
                        'notification_type': 'social_post',
                        'template_ref': f'social.post.template,{cls.test_social_template.id}',
                    }),
                ],
            })

    @users('user_eventmanager')
    def test_social_schedule_after_sub(self):
        """Check that we can not set "after each registration" with social event mail."""
        social_template = self.env['social.post.template'].create({
            'account_ids': [(4, self.social_account.id)],
            'message': 'Join the Python side of the force!',
        })
        with self.assertRaises(UserError):
            self.env['event.type'].create({
                'name': 'Super category',
                'event_type_mail_ids': [(0, 0, {
                    'template_ref': 'social.post.template,%i' % social_template.id,
                    'interval_type': 'after_sub'
                })],
            })

        with self.assertRaises(UserError):
            self.env['event.mail'].create({
                'template_ref': 'social.post.template,%i' % social_template.id,
                'interval_type': 'after_sub',
                'event_id': self.test_event.id,
            })

    @users('user_eventmanager')
    def test_social_schedule_before_event(self):
        """Check that the social template is automatically set, when changing the category of the event."""
        social_template = self.env['social.post.template'].create({
            'account_ids': [(4, self.social_account.id)],
            'message': 'Join the Python side of the force!',
        })
        category = self.env['event.type'].create({
            'name': 'Super category',
            'event_type_mail_ids': [(0, 0, {
                'notification_type': 'social_post',
                'template_ref': 'social.post.template,%i' % social_template.id,
            })],
        })
        event_form = Form(self.env['event.event'])
        event_form.name = 'Test event'
        event_form.date_begin = '2020-02-01'
        event_form.date_end = '2020-02-10'
        event_form.event_type_id = category
        event = event_form.save()

        self.assertEqual(event.name, 'Test event')
        self.assertEqual(len(event.event_mail_ids), 1)
        self.assertEqual(event.event_mail_ids.interval_type, 'before_event')
        self.assertFalse(event.event_mail_ids.mail_done)
        self.assertEqual(event.event_mail_ids.scheduled_date, datetime(2020, 1, 31, 23, 0, 0))
        self.assertEqual(event.event_mail_ids.template_ref, social_template)

        # send scheduler on event
        with self.mock_datetime_and_now(datetime(2020, 2, 2, 10, 0, 0)):
            # use sudo as schedulers are meant to be run by crons, hence limiting
            # ACLs for event users
            event.event_mail_ids.sudo().execute()

        self.assertEqual(event.event_mail_ids.mail_count_done, 1,
                         'Should equal number of accounts')
        self.assertTrue(event.event_mail_ids.mail_done)

    @mute_logger('odoo.addons.event.models.event_mail')
    @users('user_eventmanager')
    def test_social_schedule_fail_global_composer(self):
        """ Simulate a fail during composer usage e.g. invalid field path, template
        / model change, ... to check defensive behavior """
        cron = self.env.ref("event.event_mail_scheduler").sudo()
        before_scheduler = self.test_event.event_mail_ids

        def _patched_action_post(self, *args, **kwargs):
            raise ValidationError('Some error')

        with patch.object(type(self.env["social.post"]), "_action_post", _patched_action_post):
            with self.mock_datetime_and_now(self.reference_now + relativedelta(days=3)):
                cron.method_direct_trigger()
        self.assertFalse(before_scheduler.mail_done)

    @users('user_eventmanager')
    def test_social_schedule_fail_global_template_removed(self):
        """ Test flow where scheduler fails due to template ref being removed
        when sending global event communication (i.e. only through cron). """
        self.test_social_template.sudo().unlink()
        test_event = self.env['event.event'].browse(self.test_event.ids)
        before_scheduler = test_event.event_mail_ids
        self.assertFalse(before_scheduler)
