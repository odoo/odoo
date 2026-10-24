import re
from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteFonts(TransactionCase):

    def test_google_font_made_local_stores_each_file_once(self):
        # A variable font lists the same file for every weight: download and
        # store it once, else browsers fetch the same file once per weight.
        # Like Montserrat: 5 subsets x 2 styles x 9 weights = 90 src, 10 files.
        font_faces = ''.join(
            f"/* {subset} */\n@font-face {{\n  font-family: 'Montserrat';\n"
            f"  font-style: {style};\n  font-weight: {weight};\n"
            f"  src: url(https://fonts.gstatic.com/s/montserrat/v31/{subset}-{style}.woff2) format('woff2');\n}}\n"
            for style in ('normal', 'italic')
            for weight in range(100, 1000, 100)
            for subset in ('cyrillic-ext', 'cyrillic', 'vietnamese', 'latin-ext', 'latin')
        )
        requested = []

        def fake_get(url, **kwargs):
            requested.append(url)
            return Mock(content=font_faces.encode() if 'fonts.googleapis.com' in url else url.encode())

        website = self.env.ref('website.default_website')
        with patch('requests.Session.get', side_effect=fake_get):
            self.env['web_editor.assets'].with_context(website_id=website.id).make_scss_customization(
                '/website/static/src/scss/options/user_values.scss',
                {'google-local-fonts': "('Montserrat': '')"},
            )

        css = self.env['ir.attachment'].search([('name', '=', 'Montserrat (google-font)')])
        files = self.env['ir.attachment'].search([('original_id', '=', css.id)])
        src_ids = re.findall(r'/web/content/(\d+)/', css.raw.decode())
        self.assertEqual(len(src_ids), 90)
        self.assertEqual(len(files), 10)
        self.assertEqual(len(requested), 11)  # 1 request for the CSS, 10 for the font files
        self.assertEqual(set(src_ids), {str(file_id) for file_id in files.ids})
