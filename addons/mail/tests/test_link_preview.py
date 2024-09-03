# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from unittest.mock import patch

import io
import requests

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools import link_preview
from odoo.tests.common import tagged


@tagged("mail_link_preview", "mail_message", "post_install", "-at_install")
class TestLinkPreview(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_partner = cls.env['res.partner'].create({'name': 'a partner'})
        cls.existing_message = cls.test_partner.message_post(body='Test')
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

    def _patch_with_no_content_type(self, *args, **kwargs):
        content = b""""""
        return self._patched_get_html(None, content)

    def test_get_link_preview_from_url(self):
        test_cases = [
            (self._patch_with_og_properties, self.source_url),
            (self._patch_without_og_properties, self.source_url),
            (self._patch_with_image_mimetype, self.og_image),
        ]
        expected_values = [
            {
                'og_description': self.og_description,
                'og_image': self.og_image,
                'og_mimetype': None,
                'og_title': self.og_title,
                'og_type': None,
                'og_site_name': None,
                'source_url': self.source_url,
            },
            {
                'og_description': None,
                'og_image': None,
                'og_mimetype': None,
                'og_title': self.title,
                'og_type': None,
                'og_site_name': None,
                'source_url': self.source_url,
            },
            {
                'image_mimetype': 'image/png',
                'og_image': self.og_image,
                'source_url': self.og_image,
            },
        ]
        session = requests.Session()
        for (get_patch, url), expected in zip(test_cases, expected_values):
            with self.subTest(get_patch=get_patch, url=url, expected=expected), patch.object(requests.Session, 'get', get_patch):
                preview = link_preview.get_link_preview_from_url(url, session)
                self.assertEqual(preview, expected)

    def test_link_preview(self):
        with patch.object(requests.Session, 'get', self._patch_with_og_properties), patch.object(requests.Session, 'head', self._patch_head_html):
            throttle = int(self.env['ir.config_parameter'].sudo().get_param('mail.link_preview_throttle', 99))
            self.env['mail.link.preview'].create([
                {'source_url': self.source_url, 'message_id': self.existing_message.id}
                for _ in range(throttle)
            ])
            message = self.test_partner.message_post(
                body=Markup(f'<a href={self.source_url}>Nothing link</a>'),
            )
            self._reset_bus()

            def get_bus_params():
                return (
                    [(self.cr.dbname, "res.partner", self.env.user.partner_id.id)],
                    [
                        {
                            "type": "mail.record/insert",
                            "payload": {
                                "mail.link.preview": [
                                    {
                                        "id": message.link_preview_ids.id,
                                        "image_mimetype": False,
                                        "message": message.id,
                                        "og_description": self.og_description,
                                        "og_image": self.og_image,
                                        "og_mimetype": False,
                                        "og_site_name": False,
                                        "og_title": self.og_title,
                                        "og_type": False,
                                        "source_url": self.source_url,
                                    },
                                ],
                                "mail.message": self._filter_messages_fields(
                                    {
                                        "id": message.id,
                                        "linkPreviews": [message.link_preview_ids.id],
                                    },
                                ),
                            },
                        }
                    ],
                )

            with self.assertBus(get_params=get_bus_params):
                self.env["mail.link.preview"]._create_from_message_and_notify(message)
            link_preview_count = self.env["mail.link.preview"].search_count(
                [("source_url", "=", self.source_url)]
            )
            self.assertEqual(link_preview_count, throttle + 1)

    def test_link_preview_no_content_type(self):
        with patch.object(requests.Session, 'request', self._patch_with_no_content_type):
            url = self.source_url
            session = requests.Session()
            link_preview.get_link_preview_from_url(url, session)

    def test_link_preview_ignore_internal_link(self):
        """Test internal links are properly ignored from link preview."""
        with patch.object(requests.Session, "get", self._patch_with_og_properties), patch.object(
            requests.Session, "head", self._patch_head_html
        ):
            urls = [
                ("http://localhost:8069/", "http://localhost:8069/odoo", 0),
                ("http://localhost:8069/", "http://localhost:8069/odoo/test", 0),
                ("http://localhost:8069/", "http://localhost:8069/web/test", 0),
                ("http://localhost:8069/", "http://localhost:8069/", 1),
                ("http://localhost:8069/", "http://localhost:8069/odoo-experience", 1),
                ("http://localhost:8069/", "http://localhost:8069/chat/5/bFtIfYHRco", 0),
                ("https://www.odoo.com/", "https://www.odoo.com/web", 0),
                ("https://www.odoo.com/", "https://www.odoo.com/odoo", 0),
                ("https://www.odoo.com/", "https://www.odoo.com/odoo/", 0),
                ("https://www.odoo.com/", "https://www.odoo.com/odoo?debug=assets", 0),
                ("https://www.odoo.com/", "https://www.odoo.com/odoo#anchor", 0),
                ("https://www.odoo.com/", "https://www.odoo.com/odoo-experience", 1),
                ("https://www.odoo.com/", "https://www.odoo.com/odoo/1519/tasks/4102866", 0),
                ("http://www.odoo.com/", "https://www.odoo.com/odoo/1519/tasks/4102866", 1),
                ("https://www.odoo.com/", "https://wwwaodoo.com/odoo/", 1),
                ("https://www.odoo.com/", "https://www.odoo.com/chat/", 0),
                ("https://www.odoo.com/", "https://www.odoo.com/chat/5/bFtIfYHRco", 0),
                ("http://www.odoo.com/", "https://www.odoo.com/chat/5/bFtIfYHRco", 1),
                ("https://clients.odoo.com/", "https://www.odoo.com/odoo/1519/tasks/4102866", 1),
                ("https://clients.odoo.com/", "https://www.odoo.com/chat/5/bFtIfYHRco", 1),
            ]
            for request_url, url, counter in urls:
                with self.subTest(request_url=request_url, url=url, counter=counter):
                    message = self.test_partner.message_post(
                        body=Markup(f'<a href="{url}">Nothing link</a>'),
                    )
                    self.env["mail.link.preview"]._create_from_message_and_notify(
                        message, request_url
                    )
                    link_preview_count = self.env["mail.link.preview"].search_count(
                        [("message_id", "=", message.id)]
                    )
                    self.assertEqual(link_preview_count, counter)
