import base64

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestColorAssetsEditor(TransactionCase):

    # ----------------------------------------------------------
    # Setup
    # ----------------------------------------------------------
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.editor = cls.env['muk_web_colors.color_assets_editor']
        cls.light_url = '/muk_web_colors/static/src/scss/colors_light.scss'
        cls.light_bundle = 'web._assets_primary_variables'
        cls.light_custom_url = cls.editor._get_custom_colors_url(
            cls.light_url,
            cls.light_bundle,
        )
        cls.variables = [
            {'name': 'color_brand', 'value': '#112233'},
            {'name': 'color_primary', 'value': '#445566'},
        ]

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    def _cleanup_custom_asset(self):
        self.env['ir.attachment'].search([
            ('url', '=', self.light_custom_url),
        ]).unlink()
        self.env['ir.asset'].search([
            ('path', '=', self.light_custom_url),
        ]).unlink()

    # ----------------------------------------------------------
    # Tests
    # ----------------------------------------------------------
    def test_replace_creates_ir_asset_and_attachment(self):
        self._cleanup_custom_asset()
        self.editor.replace_color_variables_values(
            self.light_url,
            self.light_bundle,
            self.variables,
        )
        attachment = self.env['ir.attachment'].search([
            ('url', '=', self.light_custom_url),
        ])
        self.assertEqual(len(attachment), 1)
        asset = self.env['ir.asset'].search([
            ('path', '=', self.light_custom_url),
        ])
        self.assertEqual(len(asset), 1)
        self.assertEqual(asset.directive, 'replace')
        self.assertEqual(asset.target, self.light_url)
        self.assertTrue(asset.bundle)
        raw = attachment.datas or b''
        if isinstance(raw, str):
            raw = raw.encode('ascii')
        content = base64.b64decode(raw).decode('utf-8')
        self.assertIn('color_brand: #112233;', content)
        self.assertIn('color_primary: #445566;', content)
        self.editor.replace_color_variables_values(
            self.light_url,
            self.light_bundle,
            [{'name': 'color_brand', 'value': '#AABBCC'}],
        )
        attachment_2 = self.env['ir.attachment'].search([
            ('url', '=', self.light_custom_url),
        ])
        asset_2 = self.env['ir.asset'].search([
            ('path', '=', self.light_custom_url),
        ])
        self.assertEqual(len(attachment_2), 1)
        self.assertEqual(len(asset_2), 1)

    def test_get_values_reads_customized_file(self):
        self._cleanup_custom_asset()
        self.editor.replace_color_variables_values(
            self.light_url,
            self.light_bundle,
            self.variables,
        )
        values = self.editor.get_color_variables_values(
            self.light_url,
            self.light_bundle,
            ['color_brand', 'color_primary'],
        )
        self.assertEqual(values['color_brand'], '#112233')
        self.assertEqual(values['color_primary'], '#445566')

    def test_reset_removes_ir_asset_and_attachment(self):
        self._cleanup_custom_asset()
        self.editor.replace_color_variables_values(
            self.light_url,
            self.light_bundle,
            self.variables,
        )
        self.editor.reset_color_asset(self.light_url, self.light_bundle)
        attachment = self.env['ir.attachment'].search([
            ('url', '=', self.light_custom_url),
        ])
        asset = self.env['ir.asset'].search([
            ('path', '=', self.light_custom_url),
        ])
        self.assertFalse(attachment)
        self.assertFalse(asset)
