# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from freezegun import freeze_time
from odoo.addons.social.tests.tools import mock_void_external_calls
from odoo.addons.social_facebook.models.social_post import SocialPostFacebook
from odoo.addons.social_facebook.models.social_stream import SocialStreamFacebook
from odoo.addons.social_facebook.tests.common import SocialFacebookCommon
from unittest.mock import patch


class SocialFacebookCase(SocialFacebookCommon):
    def test_post_success(self):
        self._test_post()

    def test_post_failure(self):
        self._test_post(False)

    def _test_post(self, success=True):
        self.assertEqual(self.social_post.state, 'draft')

        def _patched_post(*args, **kwargs):
            response = requests.Response()
            if success:
                response._content = json.dumps({'id': 42}).encode('utf-8')
                response.status_code = 200
            else:
                response.status_code = 404
            return response

        with patch.object(SocialPostFacebook, '_format_images_facebook', lambda *args, **kwargs: {'media_fbid': 1}), \
             patch.object(requests, 'post', _patched_post):
                self.social_post._action_post()

        self._checkPostedStatus(success)

    @classmethod
    def _get_social_media(cls):
        return cls.env.ref('social_facebook.social_media_facebook')

    @mock_void_external_calls()
    def test_format_facebook_message(self):
        social_stream = self.env['social.stream'].create({
            'media_id': self.social_account.media_id.id,
            'account_id': self.social_account.id,
            'stream_type_id': self.env.ref('social_facebook.stream_type_page_posts').id,

        })

        message = "Hi, Social is so cool :) Thanks Odoo"
        tags = [{
            'id': 1337,
            'name': 'Odoo - Social',
            'offset': 32,
            'length': 4
        }]
        excepted_message = "Hi, Social is so cool :) Thanks @[1337] Odoo-Social"
        self.assertEqual(
            social_stream._format_facebook_message(message, tags),
            excepted_message)

        message = "Hi, Social is so cool :) Thanks Odoo @[45] thisisafaketag Tag another@[45] faketag"
        tags = [
            {
                'id': 1337,
                'name': 'Odoo - Social',
                'offset': 32,
                'length': 4
            }, {
                'id': 1338,
                'name': 'Odoo Mate and - Social',
                'offset': 58,
                'length': 3
            }]
        excepted_message = "Hi, Social is so cool :) Thanks @[1337] Odoo-Social @ [45] thisisafaketag @[1338] Odoo-Mate-and-Social another@[45] faketag"
        self.assertEqual(
            social_stream._format_facebook_message(message, tags),
            excepted_message)

    def test_format_facebook_post_date(self):
        """ Facebook has its own format to return date values.
        Let's make sure those are correctly formatted. """

        formatted_value = self.env['social.stream.post']._format_facebook_published_date({
            'created_time': "2000-07-07T09:12:30+0000"
        })
        self.assertEqual(formatted_value, '07/07/2000')

        with freeze_time('2000-07-07 09:16:30'):
            formatted_value = self.env['social.stream.post']._format_facebook_published_date({
                'created_time': "2000-07-07T09:12:30+0000"
            })
            self.assertEqual(formatted_value, '4 minutes')
