# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from functools import partial
import io

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools import link_preview
from unittest.mock import patch
import requests

discuss_channel_new_test_user = partial(mail_new_test_user, context={'discuss_channel_nosubscribe': False})


class TestLinkPreview(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = discuss_channel_new_test_user(
            cls.env, login='user_1',
            name='User 1',
            groups='base.group_user')

        cls.thread = cls.env['res.partner'].create({'name': 'a partner'})
        cls.title = 'Test title'
        cls.og_title = 'Test OG title'
        cls.og_description = 'Test OG description'
        cls.og_image = 'https://dummy-image-url.nothing'
        cls.source_url = 'https://thisdomainedoentexist.nothing'

    def _patch_head_html(self, *args, **kwargs):
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = 'text/html'
        return response

    def _patched_get_html(self, content_type, content):
        response = requests.Response()
        response.status_code = 200
        response._content = content
        # To handle chunks read on stream requests
        response.raw = io.BytesIO(response._content)
        response.headers["Content-Type"] = content_type
        return response

    def _patch_with_og_properties(self, *args, **kwargs):
        content = b"""
        <html>
        <head>
        <title>Test title</title>
        <meta property="og:title" content="Test OG title">
        <meta property="og:description" content="Test OG description">
        <meta property="og:image" content="https://dummy-image-url.nothing">
        </head>
        </html>
        """
        return self._patched_get_html('text/html', content)

    def _patch_without_og_properties(self, *args, **kwargs):
        content = b"""
        <html>
        <head>
        <title>Test title</title>
        </head>
        </html>
        """
        return self._patched_get_html('text/html', content)

    def _patch_with_image_mimetype(self, *args, **kwargs):
        content = b"""
        <html>
        <body>
        <img src='https://dummy-image-url.nothing'/>
        </body>
        </html>
        """
        return self._patched_get_html('image/png', content)

    def test_01_link_preview_throttle(self):
        with patch.object(requests.Session, 'get', self._patch_with_og_properties), patch.object(requests.Session, 'head', self._patch_head_html):
            throttle = int(self.env['ir.config_parameter'].sudo().get_param('mail.link_preview_throttle', 99))
            link_previews = []
            for _ in range(throttle):
                link_previews.append({'source_url': self.source_url, 'message_id': 1})
            self.env['mail.link.preview'].create(link_previews)
            message = self.env['mail.message'].create({
                'model': self.thread._name,
                'res_id': self.thread.id,
                'body': f'<a href={self.source_url}>Nothing link</a>',
            })
            self.env['mail.link.preview']._create_link_previews(message)
            link_preview_count = self.env['mail.link.preview'].search_count([('source_url', '=', self.source_url)])
            self.assertEqual(link_preview_count, throttle + 1)

    def test_02_link_preview_create(self):
        with patch.object(requests.Session, 'get', self._patch_with_og_properties), patch.object(requests.Session, 'head', self._patch_head_html):
            message = self.env['mail.message'].create({
                'model': self.thread._name,
                'res_id': self.thread.id,
                'body': f'<a href={self.source_url}>Nothing link</a>',
            })
            self.env['mail.link.preview']._create_link_previews(message)
            self.assertBusNotifications(
                [(self.cr.dbname, 'res.partner', self.env.user.partner_id.id)],
                message_items=[{
                    'type': 'mail.record/insert',
                    'payload': {
                        'LinkPreview': [{
                            'id': link_preview.id,
                            'message': {'id': message.id},
                            'image_mimetype': False,
                            'og_description': self.og_description,
                            'og_image': self.og_image,
                            'og_mimetype': False,
                            'og_title': self.og_title,
                            'og_type': False,
                            'source_url': self.source_url,
                        }] for link_preview in message.link_preview_ids
                    }
                }]
            )

    def test_get_link_preview_from_url(self):
        test_cases = [
            (self._patch_with_og_properties, self.source_url),
            (self._patch_without_og_properties, self.source_url),
            (self._patch_with_image_mimetype, self.og_image),
        ]
        test_asserts = [
            {
                'og_description': self.og_description,
                'og_image': self.og_image,
                'og_mimetype': None,
                'og_title': self.og_title,
                'og_type': None,
                'source_url': self.source_url,
            },
            {
                'og_description': None,
                'og_image': None,
                'og_mimetype': None,
                'og_title': self.title,
                'og_type': None,
                'source_url': self.source_url,
            },
            {
                'image_mimetype': 'image/png',
                'og_image': self.og_image,
                'source_url': self.og_image,
            },
        ]
        session = requests.Session()
        for (get_patch, url), expected in zip(test_cases, test_asserts):
            with self.subTest(get_patch=get_patch, url=url, expected=expected), patch.object(requests.Session, 'get', get_patch):
                preview = link_preview.get_link_preview_from_url(url, session)
                self.assertEqual(preview, expected)
