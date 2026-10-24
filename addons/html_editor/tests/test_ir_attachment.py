from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestIrAttachmentWebEditor(TransactionCase):
    def test_compute_image_src_empty_checksum(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'test.png',
            'type': 'binary',
            'mimetype': 'image/png',
            'datas': False,
        })
        self.assertFalse(attachment.checksum, "Checksum should be False for empty datas")

        expected_url = f'/web/image/{attachment.id}-0/test.png'
        self.assertEqual(attachment.image_src, expected_url)

    def test_image_src_for_url_attachment_without_url(self):
        """That that URL attachment without a URL uses the image redirect URL."""
        attachment = self.env['ir.attachment'].create({
            'name': 'test attachment',
            'type': 'url',
            'mimetype': 'image/jpeg',
        })

        expected_url = f'/web/image/{attachment.id}-redirect/test%20attachment'
        self.assertEqual(attachment.image_src, expected_url)
