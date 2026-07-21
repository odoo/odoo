# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestIrAttachment(TransactionCase):

    def test_post_add_create_preserves_mimetype(self):
        def _generate_cloud_storage_url(self):
            """ Mock _generate_cloud_storage_url to avoid NotImplementedError"""
            return f"http://cloud.storage/{self.id}"

        # Patch the method on the class to avoid "read-only" errors on recordsets
        self.patch(self.env.registry['ir.attachment'], '_generate_cloud_storage_url', _generate_cloud_storage_url)

        self.env['ir.config_parameter'].sudo().set_param('cloud_storage_provider', 'dummy')
        attachment = self.env['ir.attachment'].create({
            'name': 'test_audio.webm',
            'mimetype': 'audio/webm',
            'raw': b'dummy content',
        })
        attachment._post_add_create(cloud_storage=True)

        self.assertEqual(attachment.type, 'cloud_storage')
        self.assertEqual(attachment.mimetype, 'audio/webm', "Attachment mimetype should be preserved")
        self.assertFalse(attachment.raw, "Raw data should be cleared")
        self.assertEqual(attachment.url, f"http://cloud.storage/{attachment.id}")
