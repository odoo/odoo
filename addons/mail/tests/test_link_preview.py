# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from functools import partial

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from unittest.mock import patch
import requests

mail_channel_new_test_user = partial(mail_new_test_user, context={'mail_channel_nosubscribe': False})


def _patched_get_html(*args, **kwargs):
    response = requests.Response()
    response.status_code = 200
    response._content = b"""
    <html>
    <head>
    <meta property="og:title" content="Test title">
    <meta property="og:description" content="Test description">
    </head>
    </html>
    """
    response.headers["Content-Type"] = 'text/html'
    return response

def _patch_head_html(*args, **kwargs):
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Type"] = 'text/html'
    return response


class TestLinkPreview(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = mail_channel_new_test_user(
            cls.env, login='user_1',
            name='User 1',
            groups='base.group_user')

        cls.public_channel = cls.env['mail.channel'].create({
            'name': 'Public channel of user 1',
            'channel_type': 'channel',
        })
        cls.public_channel.channel_member_ids.unlink()

    def test_01_link_preview_throttle(self):
        with patch.object(requests.Session, 'get', _patched_get_html), patch.object(requests.Session, 'head', _patch_head_html):
            throttle = int(self.env['ir.config_parameter'].sudo().get_param('mail.link_preview_throttle', 99))
            link_previews = []
            for _ in range(throttle):
                link_previews.append({'source_url': 'https://thisdomainedoentexist.nothing', 'message_id': 1})
            self.env['mail.link.preview'].create(link_previews)
            message = self.env['mail.message'].create({
                'model': 'mail.channel',
                'res_id': self.public_channel.id,
                'body': '<a href="https://thisdomainedoentexist.nothing">Nothing link</a>',
            })
            self.env['mail.link.preview']._create_link_previews(message)
            link_preview_count = self.env['mail.link.preview'].search_count([('source_url', '=', 'https://thisdomainedoentexist.nothing')])
            self.assertEqual(link_preview_count, throttle + 1)

    def test_02_link_preview_create(self):
        with patch.object(requests.Session, 'get', _patched_get_html), patch.object(requests.Session, 'head', _patch_head_html):
            message = self.env['mail.message'].create({
                'model': 'mail.channel',
                'res_id': self.public_channel.id,
                'body': '<a href="https://thisdomainedoentexist.nothing">Nothing link</a>',
            })
            self.env['mail.link.preview']._create_link_previews(message)
            self.assertBusNotifications(
                [(self.cr.dbname, 'mail.channel', self.public_channel.id)],
                message_items=[{
                    'type': 'mail.link.preview/insert',
                    'payload': [{
                        'id': link_preview.id,
                        'message': {'id': message.id},
                        'image_mimetype': False,
                        'og_description': 'Test description',
                        'og_image': False,
                        'og_mimetype': False,
                        'og_title': 'Test title',
                        'og_type': False,
                        'source_url': 'https://thisdomainedoentexist.nothing',
                    } for link_preview in message.link_preview_ids]
                }]
            )
