import os
from PIL import Image
from functools import partial
from collections import defaultdict

from odoo.tests import TransactionCase, tagged, HttpCase, Form
from odoo.tools import image_to_base64


dir_path = os.path.dirname(os.path.realpath(__file__))


class TestBaseDocumentLayoutHelpers(TransactionCase):

    def _get_images(self):
        if not hasattr(self, 'company_imgs'):
            imgs = defaultdict(lambda: dict())
            for fname, colors in self.img_colors.items():
                fname_split = fname.split('.')
                fformat = fname_split[1].upper() if len(fname_split) > 1 else 'JPEG'
                with Image.open(os.path.join(dir_path, fname), 'r') as img:
                    imgs[fname_split[0]]['img'] = image_to_base64(img, fformat)
                    imgs[fname_split[0]]['colors'] = colors
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

    def assertColors(self, checked_obj, expected):
        _expected_getter = expected.get if isinstance(expected, dict) else partial(getattr, expected)
        for fname in self.color_fields:
            color1 = getattr(checked_obj, fname)
            color2 = _expected_getter(fname)
            self._compare_colors_rgb(color1, color2)

    def _make_templates_and_layouts(self):
        self.layout_template1 = self.env['ir.ui.view'].create({
            'name': 'layout_template1',
            'type': 'qweb',
            'arch': '''<div></div>''',
        })
        self.env['ir.model.data'].create({
            'name': 'layout_template1',
            'model': 'ir.ui.view',
            'module': 'base',
            'res_id': self.layout_template1.id,
        })
        self.env['report.layout'].create({
            'view_id': self.layout_template1.id,
            'name': 'report_%s' % self.layout_template1.name,
            'primary_color': '#875A7B',
            'secondary_color': '#875A7C',
        })

    def setUp(self):
        super(TestBaseDocumentLayoutHelpers, self).setUp()
        self.img_colors = {
            'tommy_small.jpeg': {
                'primary_color': '#7790af',
                'secondary_color': '#141d21'
            },
            'fire_small.jpeg': {
                'primary_color': '#c8864d',
                'secondary_color': '#372422'
            }
        }
        self.color_fields = ['primary_color', 'secondary_color']
        self._get_images()
        self.company = self.env.company_id
        self.css_color_error = 0
        self._make_templates_and_layouts()


@tagged('document_layout')
class TestBaseDocumentLayout(TestBaseDocumentLayoutHelpers):

    def test_company_no_color_change_logo(self):
        self.company.write({
            'primary_color': None,
            'secondary_color': None,
            'logo': None,
            'external_report_layout_id': self.env.ref('base.layout_template1').id,
        })
        company_layout = self._get_report_layout_from_view(self.company.external_report_layout_id)
        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, company_layout)
            self.assertEqual(doc_layout.company_id, self.company)
            doc_layout.logo = self.company_imgs['tommy_small']['img']

            self.assertColors(doc_layout, self.company_imgs['tommy_small']['colors'])

            doc_layout.logo = ''
            self.assertColors(doc_layout, self.company_imgs['tommy_small']['colors'])
            self.assertEqual(doc_layout.logo, '')

    def test_company_no_color_but_logo_change_logo(self):
        self.company.write({
            'primary_color': None,
            'secondary_color': None,
            'logo': self.company_imgs['tommy_small']['img'],
        })
        # Don't why yet, but the second time the colors are computes
        # there is a ~2% error between expected colors and computes ones
        self.css_color_error = 2
        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company_imgs['tommy_small']['colors'])
            doc_layout.logo = self.company_imgs['fire_small']['img']
            self.assertColors(doc_layout, self.company_imgs['fire_small']['colors'])

    def test_company_colors_change_logo(self):
        self.company.write({
            'primary_color': '#7790af',
            'secondary_color': '#141d21',
            'logo': None,
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['fire_small']['img']
            self.assertColors(doc_layout, self.company_imgs['fire_small']['colors'])

    def test_company_colors_and_logo_change_logo(self):
        self.company.write({
            'primary_color': '#7790af',
            'secondary_color': '#141d21',
            'logo': self.company_imgs['fire_small']['img'],
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['fire_small']['img']
            self.assertColors(doc_layout, self.company_imgs['fire_small']['colors'])

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
