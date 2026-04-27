# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields
from odoo.tests import Form
from odoo.addons.social.tests import common
from odoo.addons.social.tests.tools import mock_void_external_calls
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.sql_db import Cursor
from odoo.tests.common import users, tagged


@tagged("utm")
class TestSocialBasics(common.SocialCase, CronMixinCase):
    @mock_void_external_calls()
    def test_cron_triggers(self):
        """ When scheduling social posts, CRON triggers should be created to run the CRON sending
        the post as close to the time frame as possible. """

        scheduled_date = fields.Datetime.now() + timedelta(days=1)
        with self.capture_triggers('social.ir_cron_post_scheduled') as captured_triggers:
            social_post = self.env['social.post'].create({
                'account_ids': [(4, self.social_account.id)],
                'message': 'Test CRON triggers',
                'post_method': 'scheduled',
                'scheduled_date': scheduled_date
            })

        self.assertEqual(len(captured_triggers.records), 1)
        captured_trigger = captured_triggers.records[0]
        self.assertEqual(captured_trigger.call_at, scheduled_date)
        self.assertEqual(captured_trigger.cron_id, self.env.ref('social.ir_cron_post_scheduled'))

        # When updating the scheduled date, a new CRON trigger should be created with the new date.
        # Note that we intentionally do not remove / update the old trigger, as we would complicate
        # the code and it's not necessary (CRON triggers are rather harmless and cleaned
        # automatically anyway)
        with self.capture_triggers('social.ir_cron_post_scheduled') as captured_triggers:
            social_post.write({'scheduled_date': scheduled_date + timedelta(hours=1)})

        self.assertEqual(len(captured_triggers.records), 1)
        captured_trigger = captured_triggers.records[0]
        self.assertEqual(captured_trigger.call_at, scheduled_date + timedelta(hours=1))
        self.assertEqual(captured_trigger.cron_id, self.env.ref('social.ir_cron_post_scheduled'))

    @users('social_manager')
    @mock_void_external_calls()
    def test_social_account_internals(self):
        """ Test social account creation, notably medium generation """
        vals_list = [{
            'name': 'TestAccount_%d' % x,
            'media_id': self.social_media.id,
        } for x in range(0, 5)]
        accounts = self.env['social.account'].create(vals_list)
        self.assertEqual(len(accounts.utm_medium_id), 5)
        self.assertEqual(
            set(accounts.mapped('utm_medium_id.name')),
            set(["[%s] TestAccount_%d" % (self.social_media.name, x) for x in range(0, 5)])
        )

        first_account = accounts[0]
        first_account.write({'name': 'Some Updated Name'})
        self.assertEqual(
            first_account.utm_medium_id.name,
            "[%s] Some Updated Name" % self.social_media.name
        )

    @users('social_user')
    @mock_void_external_calls()
    def test_social_post_create_multi(self):
        """ Ensure that a 'multi' creation of 2 social.posts also
        creates 2 associated utm.sources. """
        social_posts = self.env['social.post'].create([{
            'account_ids': [(4, self.social_account.id)],
            'message': 'Message 1'
        }, {
            'account_ids': [(4, self.social_account.id)],
            'message': 'Message 2'
        }])

        self.assertEqual(2, len(social_posts))
        self.assertEqual(2, len(social_posts.source_id))
        self.assertNotEqual(social_posts[0].source_id, social_posts[1].source_id)

    @freeze_time('2022-01-02')
    @patch.object(Cursor, 'now', lambda *args, **kwargs: datetime(2022, 1, 2))
    @users('social_user')
    def test_social_post_utm(self):
        """Test that the name of the UTM source is generated from the message of the post."""
        post_1, post_2, post_3, post_4, post_5, post_6, post_7 = self.env['social.post'].create([{
            'account_ids': [(4, self.social_account.id)],
            'message': 'Message 1',
        }, {
            'account_ids': [(4, self.social_account.id)],
            'message': 'Message 1',
        }, {
            'account_ids': [(4, self.social_account.id)],
            'message': 'Message 1',
            'name': 'Source Name Social Post (Social Post created on 2022-01-02)',
        }, {
            'account_ids': [(4, self.social_account.id)],
            'message': 'Message 2',
            'name': 'Message 1 (Social Post created on 2022-01-02) [1337]',
        }, {
            'account_ids': [(4, self.social_account.id)],
            'message': 'Source Name Social Post',
        }, {
            'account_ids': [(4, self.social_account.id)],
            'message': 'Long message %s' % ('x' * 500),
        }, {
            'account_ids': [(4, self.social_account.id)],
            'message': 'Long message %s different' % ('x' * 500),
        }])

        self.assertEqual(post_1.name, 'Message 1 (Social Post created on 2022-01-02)',
            msg='Should have generated the name from the post message')
        self.assertEqual(post_2.name, 'Message 1 (Social Post created on 2022-01-02) [2]',
            msg='Should have added a counter at the end of the name')
        self.assertEqual(post_3.name, 'Source Name Social Post (Social Post created on 2022-01-02)',
            msg='Should not have generated the name from the content')
        self.assertEqual(post_4.name, 'Message 1 (Social Post created on 2022-01-02) [1337]',
            msg='Should have kept the counter of the given name when possible to respect user input')
        self.assertEqual(post_5.name, 'Source Name Social Post (Social Post created on 2022-01-02) [2]',
            msg='Name already generated from the content of a different record')

        # The 2 next social posts have different message, but they are the same once truncated
        self.assertEqual(post_6.name, 'Long message xxxxxxx... (Social Post created on 2022-01-02)',
            msg='Should have truncated the message')
        self.assertEqual(post_7.name, 'Long message xxxxxxx... (Social Post created on 2022-01-02) [2]',
            msg='Should have truncated the message and added a counter at the end')

    @freeze_time('2022-01-02')
    @patch.object(Cursor, 'now', lambda *args, **kwargs: datetime(2022, 1, 2))
    @users('social_user')
    def test_social_post_image_utm(self):
        attachments = self.env['ir.attachment'].create([{
            'name': 'first.png',
            'datas': 'ABCDEFG='
        }, {
            'name': 'second.png',
            'datas': 'GFEDCBA='
        }]).ids
        image_post = self.env['social.post'].create({
            'account_ids': [(4, self.social_account.id)],
            'image_ids': [(4, aid) for aid in attachments]})
        self.assertEqual(image_post.name, 'Post (Social Post created on 2022-01-02)',
            msg='Should have generated custom message for image post')
        image_post.message = 'Message image'
        self.assertEqual(image_post.name, 'Message image (Social Post created on 2022-01-02)',
            msg='Should have generated the name from the post message')

    def test_social_post_create_with_default_calendar_date(self):
        """ Make sure that when a default_calendar_date is passed and the scheduled_date is changed,
        We take into account the new scheduled_date as calendar_date.
        See social.post#create for more details."""
        default_calendar_date = fields.Datetime.now() + timedelta(hours=1)
        form = Form(self.env['social.post'].with_context(default_calendar_date=default_calendar_date))
        form.message = 'this is a message'
        self.assertEqual(form.scheduled_date, default_calendar_date)
        new_scheduled_date = default_calendar_date + timedelta(minutes=20)
        form.scheduled_date = new_scheduled_date
        post = form.save()
        self.assertEqual(post.calendar_date, new_scheduled_date)
        self.assertEqual(post.scheduled_date, new_scheduled_date)

    @classmethod
    def _get_social_media(cls):
        return cls.env['social.media'].create({
            'name': 'Social Media',
        })
