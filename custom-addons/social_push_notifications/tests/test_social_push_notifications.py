# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import random

from unittest.mock import patch

from odoo import fields
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.social.tests.common import SocialCase
from odoo.addons.social.models.social_post import SocialPost
from odoo.addons.social_push_notifications.models.social_account import SocialAccountPushNotifications


class SocialPushNotificationsCase(SocialCase, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        super(SocialPushNotificationsCase, cls).setUpClass()

        cls.website_1 = cls.env['website'].create({
            'name': 'Website 1 WITHOUT push notifications',
            'domain': 'website1.example.com',
            'firebase_enable_push_notifications': False,
        })
        cls.website_2 = cls.env['website'].create({
            'name': 'Website 2 WITH push notifications',
            'domain': 'website2.example.com',
            'firebase_enable_push_notifications': True,
            'firebase_use_own_account': True,
            'firebase_admin_key_file': base64.b64encode(b'{}')
        })
        cls.website_3 = cls.env['website'].create({
            'name': 'Website 3 WITH push notifications',
            'domain': 'website3.example.com',
            'firebase_enable_push_notifications': True,
            'firebase_use_own_account': True,
            'firebase_admin_key_file': base64.b64encode(b'{}')
        })
        cls.websites = cls.website_1 | cls.website_2 | cls.website_3

        cls.social_accounts = cls.env['social.account'].search(
            [('website_id', 'in', cls.websites.ids)]
        )

        cls.social_post.invalidate_model(['account_allowed_ids'])
        cls.social_post.write({
            'account_ids': [(6, 0, cls.social_accounts.filtered(lambda a: a.website_id.id != cls.website_3.id).ids)],
        })

    def test_post(self):
        """ Test a full flow of posting social_push_notifications.
        We trigger the send method of the post and check that it does all the way to the Firebase
        sending calls. """

        # Create some visitors with or without push_token in different timezone (or no timezone)
        timezones = ['Europe/Brussels', 'America/New_York', 'Asia/Vladivostok', False]
        Visitor = self.env['website.visitor']
        visitor_vals = []
        for i in range(0, 4):
            visitor_vals.append({
                'name': timezones[i] or 'Visitor',
                'timezone': timezones[i],
                'access_token': '%032x' % random.randrange(16**32),
                'push_subscription_ids': [(0, 0, {'push_token': 'fake_token_%s' % i})] if i != 0 else False,
                'website_id': self.websites[i].id if i != 3 else False,
            })
        self.visitors = Visitor.create(visitor_vals)
        self.social_post.create_uid.write({'tz': timezones[0]})

        # Since mocking a decorated method doesn't work, we unset the constrains
        # before creating the post and re-apply them after.
        check_scheduled_date_constrains = SocialPost._check_scheduled_date._constrains
        SocialPost._check_scheduled_date._constrains = tuple()

        scheduled_date = fields.Datetime.now() - datetime.timedelta(minutes=1)
        with self.capture_triggers('social.ir_cron_post_scheduled') as captured_triggers:
            self.social_post.write({
                'use_visitor_timezone': True,
                'post_method': 'scheduled',
                'scheduled_date': scheduled_date
            })

        SocialPost._check_scheduled_date._constrains = check_scheduled_date_constrains

        # when scheduling, a CRON trigger is created to match the scheduled_date
        self.assertEqual(len(captured_triggers.records), 1)
        captured_trigger = captured_triggers.records[0]
        self.assertEqual(captured_trigger.call_at, scheduled_date)
        self.assertEqual(captured_trigger.cron_id, self.env.ref('social.ir_cron_post_scheduled'))

        self.assertEqual(self.social_post.state, 'draft')

        with self.capture_triggers('social.ir_cron_post_scheduled') as captured_triggers:
            self.social_post._action_post()  # begin the post process

        # as the post_method is 'scheduled', a CRON trigger should not be created, we already have one
        self.assertEqual(len(captured_triggers.records), 0)

        # check that live posts are correctly created
        live_posts = self.env['social.live.post'].search([('post_id', '=', self.social_post.id)])
        self.assertEqual(len(live_posts), 2)

        self.assertTrue(all(live_post.state == 'ready' for live_post in live_posts))
        self.assertEqual(self.social_post.state, 'posting')

        def _firebase_send_message_from_configuration(_this, _data, visitors):
            website = visitors.website_id
            push_enabled = website.firebase_enable_push_notifications
            # Ensure that only visitors from the website with push notifications enabled
            # and linked to the social account are notified
            self.assertEqual(len(visitors), 1 if push_enabled else 0)
            if visitors:
                self.assertEqual(visitors.website_id, self.website_2)
            return visitors.mapped('push_subscription_ids.push_token'), []

        with patch.object(SocialAccountPushNotifications, '_firebase_send_message_from_configuration',
             _firebase_send_message_from_configuration):
            live_posts._post_push_notifications()

        self.assertFalse(all(live_post.state == 'posted' for live_post in live_posts))
        self.assertEqual(self.social_post.state, 'posting')

        # simulate that everyone can receive the push notif (because their time >= time of the one who created the post)
        self.visitors.write({'timezone': self.env.user.tz})

        with patch.object(SocialAccountPushNotifications, '_firebase_send_message_from_configuration',
             _firebase_send_message_from_configuration):
            live_posts._post_push_notifications()

        self._checkPostedStatus(True)

    @classmethod
    def _get_social_media(cls):
        return cls.env.ref('social_push_notifications.social_media_push_notifications')
