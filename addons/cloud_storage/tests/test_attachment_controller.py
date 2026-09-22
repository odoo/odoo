# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import zipfile
from unittest.mock import patch
from urllib.parse import urlsplit

import requests

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.http import Request
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestCloudStorageAttachmentController(HttpCaseWithUserDemo):

    def test_cloud_storage_attachment_zip(self):
        """Downloading a mixed ZIP includes every cloud and local file with its original contents."""

        self.env['ir.config_parameter'].sudo().set_param('cloud_storage_provider', 'dummy')
        self.patch(self.env.registry['res.config.settings'], '_get_cloud_storage_configuration',
                   lambda self: {'provider': 'dummy'})
        self.patch(self.env.registry['ir.attachment'], '_generate_cloud_storage_url',
                   lambda self: f'https://cloud.storage/{self.name}')
        self.patch(self.env.registry['ir.attachment'], '_generate_cloud_storage_download_info',
                   lambda self: {'url': self.url})

        self.authenticate(self.user_demo.login, self.user_demo.login)

        attachments = self.env['ir.attachment'].with_user(self.user_demo).create([
            {'name': 'first.txt', 'raw': b'first cloud file', 'mimetype': 'text/plain'},
            {'name': 'second.txt', 'raw': b'second cloud file', 'mimetype': 'text/plain'},
            {'name': 'local.txt', 'raw': b'local file', 'mimetype': 'text/plain'},
        ])
        cloud_attachments = attachments[:2]
        contents = {attachment.name: attachment.raw for attachment in attachments}
        cloud_attachments.sudo()._post_add_create(cloud_storage=True)

        def download_cloud_file(url, **kwargs):
            parsed = urlsplit(url)
            response = requests.Response()
            response.status_code = 200
            response._content = contents[parsed.path.rsplit('/', 1)[-1]]
            return response

        with patch('odoo.addons.cloud_storage.models.ir_attachment.requests.get', side_effect=download_cloud_file):
            response = self.url_open('/mail/attachment/zip', data={
                'file_ids': ','.join(map(str, attachments.ids)),
                'zip_name': 'attachments.zip',
                'csrf_token': Request.csrf_token(self),
            })

        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertCountEqual(archive.namelist(), contents)
            for name, content in contents.items():
                self.assertEqual(archive.read(name), content)
