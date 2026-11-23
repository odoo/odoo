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

    def test_save_asset_keeps_mimetype(self):
        assets = self.env['web_editor.assets']
        url = '/web_editor/static/src/scss/web_editor.variables.scss'
        bundle = 'web_editor.wysiwyg_iframe_editor_assets'
        custom_url = assets._make_custom_asset_url(url, bundle)

        assets.save_asset(url, bundle, '$test: 1;', 'scss')
        attachment = self.env['ir.attachment'].search([('url', '=', custom_url)])
        self.assertEqual(attachment.mimetype, 'text/scss')

        # The mimetype is preserved when the asset is updated.
        assets.save_asset(url, bundle, '$test: 2;', 'scss')
        self.assertEqual(attachment.mimetype, 'text/scss')
