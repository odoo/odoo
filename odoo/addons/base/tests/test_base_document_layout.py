import os
from PIL import Image
from functools import partial

from odoo.tests import TransactionCase, tagged, HttpCase, Form
from odoo.tools import image_to_base64

dir_path = os.path.dirname(os.path.realpath(__file__))


@tagged('document_layout')
class TestBaseDocumentLayout(TransactionCase):

    def _get_images(self):
        if not hasattr(self, 'company_imgs'):
            imgs = {}
            for fname in self.file_names:
                with Image.open(os.path.join(dir_path, fname), 'r') as img:
                    fname_split = fname.split('.')
                    fformat = fname_split[1].upper()
                    imgs[fname_split[0]] = image_to_base64(img, fformat)
            self.company_imgs = imgs
        return self.company_imgs

    def _get_report_layout_from_view(self, view):
        layout = self.env["report.layout"].search([
            ('view_id.key', '=', view.key)
        ])
        self.assertTrue(layout.exists())
        return layout

    def _color_rgb_hex_to_ints(self, color):
        color = color.split('#')[1]
        res = []
        step = 2
        num_colors = len('RGB') * step
        for i in range(0, num_colors, step):
            res.append(int(color[i:i + step], 16))
        return res

    def _compare_colors_rgb(self, color1, color2):
        self.assertEqual(bool(color1), bool(color2))
        if not color1:
            return
        color1 = self._color_rgb_hex_to_ints(color1)
        color2 = self._color_rgb_hex_to_ints(color2)
        self.assertEqual(len(color1), len(color2))
        for i in range(len(color1)):
            self.assertAlmostEqual(color1[i], color2[i], delta=self.css_color_error)

    def assert_colors(self, checked_obj, expected):
        _expected_getter = expected.get if isinstance(expected, dict) else partial(getattr, expected)
        for fname in self.color_fields:
            color1 = getattr(checked_obj, fname)
            color2 = _expected_getter(fname)
            self._compare_colors_rgb(color1, color2)

    def setUp(self):
        super(TestBaseDocumentLayout, self).setUp()
        self.file_names = ['tommy_small.jpeg', 'fire_small.jpeg']
        self.color_fields = ['primary_color', 'secondary_color']
        self._get_images()
        self.company = self.env.company_id
        self.css_color_error = 2

    def test_company_no_color_change_logo(self):
        self.company.write({
            'primary_color': None,
            'secondary_color': None,
            'logo': None,
        })
        company_layout = self._get_report_layout_from_view(self.company.external_report_layout_id)
        with Form(self.env['base.document.layout']) as doc_layout:
            self.assert_colors(doc_layout, company_layout)
            self.assertEqual(doc_layout.company_id, self.company)
            doc_layout.logo = self.company_imgs['tommy_small']
            logo_colors = {
                'primary_color': '#7790af',
                'secondary_color': '#141d21'
            }
            self.assert_colors(doc_layout, logo_colors)

            doc_layout.logo = ''
            self.assert_colors(doc_layout, logo_colors)
            self.assertEqual(doc_layout.logo, '')

    def test_company_no_color_but_logo_change_logo(self):
        self.company.write({
            'primary_color': None,
            'secondary_color': None,
            'logo': self.company_imgs['tommy_small'],
        })
        with Form(self.env['base.document.layout']) as doc_layout:
            origin_colors = {
                'primary_color': '#7790af',
                'secondary_color': '#141d21'
            }
            self.assert_colors(doc_layout, origin_colors)
            doc_layout.logo = self.company_imgs['fire_small']
            logo_colors = {
                'primary_color': '#c8864d',
                'secondary_color': '#372422'
            }
            self.assert_colors(doc_layout, logo_colors)

    def test_company_colors_change_logo(self):
        self.company.write({
            'primary_color': '#7790af',
            'secondary_color': '#141d21',
            'logo': None,
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assert_colors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['fire_small']
            logo_colors = {
                'primary_color': '#c8864d',
                'secondary_color': '#372422'
            }
            self.assert_colors(doc_layout, logo_colors)

    def test_company_colors_and_logo_change_logo(self):
        self.company.write({
            'primary_color': '#7790af',
            'secondary_color': '#141d21',
            'logo': self.company_imgs['fire_small'],
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assert_colors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['fire_small']
            logo_colors = {
                'primary_color': '#c8864d',
                'secondary_color': '#372422'
            }
            self.assert_colors(doc_layout, logo_colors)

    def test_default_color_flag(self):
        """ use_default_colors should be false when both primary_color and secondary_color are set """

        #FIXME wizard require a company

        # wizard = self.env['base.document.layout'].create({})
        # self.assertTrue(wizard.use_default_colors, "when no colors are set, use_default_colors should default to true")

        # wizard = self.env['base.document.layout'].create({
        #     'primary_color':'#000000',
        #     'secondary_color':'#000000',
        # })
        # self.assertFalse(wizard.use_default_colors, "when both colors are set, use_default_colors should default to false")

        pass

@tagged('document_layout_ui')
class TestBaseDocumentLayoutUI(HttpCase):
    def test_tour(self):
        """ base document layout wizard tour """
        #TODO implementation
        pass
        # self.start_tour("URL", "test_base_document_layout", login="USER_TYPE")
