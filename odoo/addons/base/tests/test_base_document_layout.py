import os
from PIL import Image
from functools import partial

from odoo.tests import TransactionCase, tagged, HttpCase, Form
from odoo.tools import image_to_base64, frozendict


dir_path = os.path.dirname(os.path.realpath(__file__))
_file_cache = {}


class TestBaseDocumentLayoutHelpers(TransactionCase):
    #
    #   Public
    #
    def setUp(self):
        super(TestBaseDocumentLayoutHelpers, self).setUp()
        self.color_fields = ['primary_color', 'secondary_color']
        self.company = self.env.company_id
        self.css_color_error = 0
        self._set_templates_and_layouts()
        self._set_images()

    def assertColors(self, checked_obj, expected):
        _expected_getter = expected.get if isinstance(expected, dict) else partial(getattr, expected)
        for fname in self.color_fields:
            color1 = getattr(checked_obj, fname)
            color2 = _expected_getter(fname)
            if self.css_color_error:
                self._compare_colors_rgb(color1, color2)
            else:
                self.assertEqual(color1, color2)

    #
    #   Private
    #
    def _color_rgb_hex_to_ints(self, color):
        color = color.split('#')[1]
        res = []
        step = 2
        num_colors = len(color) // step
        self.assertFalse(len(color) % step)
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

    def _get_images_for_test(self):
        return {
            'tommy_small.jpeg': {
                'primary_color': '#7790af',
                'secondary_color': '#141d21'
            },
            'fire_small.jpeg': {
                'primary_color': '#c8864d',
                'secondary_color': '#372422'
            }
        }

    def _set_images(self):
        for fname, colors in self._get_images_for_test().items():
            fname_split = fname.split('.')
            fformat = fname_split[1].upper() if len(fname_split) > 1 else 'JPEG'
            if not fname_split[0] in _file_cache:
                with Image.open(os.path.join(dir_path, fname), 'r') as img:
                    _img = frozendict({
                        'img': image_to_base64(img, fformat),
                        'colors': colors,
                    })
                    _file_cache[fname_split[0]] = _img
        self.company_imgs = frozendict(_file_cache)

    def _set_templates_and_layouts(self):
        self.layout_template1 = self.env['ir.ui.view'].create({
            'name': 'layout_template1',
            'key': 'layout_template1',
            'type': 'qweb',
            'arch': '''<div></div>''',
        })
        self.env['ir.model.data'].create({
            'name': self.layout_template1.name,
            'model': 'ir.ui.view',
            'module': 'base',
            'res_id': self.layout_template1.id,
        })
        self.report_layout1 = self.env['report.layout'].create({
            'view_id': self.layout_template1.id,
            'name': 'report_%s' % self.layout_template1.name,
            'primary_color': '#875A7B',
            'secondary_color': '#875A7C',
        })
        self.layout_template2 = self.env['ir.ui.view'].create({
            'name': 'layout_template2',
            'key': 'layout_template2',
            'type': 'qweb',
            'arch': '''<div></div>''',
        })
        self.env['ir.model.data'].create({
            'name': self.layout_template2.name,
            'model': 'ir.ui.view',
            'module': 'base',
            'res_id': self.layout_template2.id,
        })
        self.report_layout2 = self.env['report.layout'].create({
            'view_id': self.layout_template2.id,
            'name': 'report_%s' % self.layout_template2.name,
            'primary_color': '#777777',
            'secondary_color': '#777777',
        })


@tagged('document_layout')
class TestBaseDocumentLayout(TestBaseDocumentLayoutHelpers):
    # Logo change Tests
    def test_company_no_color_change_logo(self):
        """When neither a logo nor the colors are set
        The wizard displays the colors of the report layout
        Changing logo means the colors on the wizard change too
        Emptying the logo works and doesn't change the colors"""
        self.company.write({
            'primary_color': False,
            'secondary_color': False,
            'logo': False,
            'external_report_layout_id': self.env.ref('base.layout_template1').id,
        })
        company_layout = self.report_layout1
        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, company_layout)
            self.assertEqual(doc_layout.company_id, self.company)
            doc_layout.logo = self.company_imgs['tommy_small']['img']

            self.assertColors(doc_layout, self.company_imgs['tommy_small']['colors'])

            doc_layout.logo = ''
            self.assertColors(doc_layout, self.company_imgs['tommy_small']['colors'])
            self.assertEqual(doc_layout.logo, '')

    def test_company_no_color_but_logo_change_logo(self):
        """When company colors are not set, but a logo is,
        the wizard displays the computed colors from the logo"""
        self.company.write({
            'primary_color': False,
            'secondary_color': False,
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
        """changes of the logo implies displaying the new computed colors"""
        self.company.write({
            'primary_color': '#7790af',
            'secondary_color': '#141d21',
            'logo': False,
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['fire_small']['img']
            self.assertColors(doc_layout, self.company_imgs['fire_small']['colors'])

    def test_company_colors_and_logo_change_logo(self):
        """The colors of the company may differ from the one the logo computes
        Opening the wizard in these condition displays the company's colors
        When the logo changes, colors must change according to the logo"""
        self.company.write({
            'primary_color': '#7790af',
            'secondary_color': '#141d21',
            'logo': self.company_imgs['fire_small']['img'],
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['fire_small']['img']
            self.assertColors(doc_layout, self.company_imgs['fire_small']['colors'])

    # Layout change tests
    def test_company_colors_and_layout_change_layout(self):
        """When the logo is not set on the company
        but colors and layout templates are,
        keep company colors in the wizard"""
        self.company.write({
            'primary_color': '#666666',
            'secondary_color': '#666666',
            'external_report_layout_id': self.layout_template1.id,
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.report_layout_id = self.report_layout2
            self.assertColors(doc_layout, self.company)

    def test_company_no_colors_no_logo_and_layout_change_layout(self):
        """When neither the logo nor the company's colors are set,
        change the wizard's colors according to the template"""
        self.company.write({
            'primary_color': False,
            'secondary_color': False,
            'external_report_layout_id': self.layout_template1.id,
            'logo': False,
        })
        company_layout = self.report_layout1
        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, company_layout)
            doc_layout.report_layout_id = self.report_layout2
            self.assertColors(doc_layout, self.report_layout2)

    # /!\ This case is NOT supported, and probably not supportable
    # res.partner resizes manu-militari the image it is given
    # so res.company._get_logo differs from res.partner.[default image]
    # def test_company_no_colors_default_logo_and_layout_change_layout(self):
    #     """When the default YourCompany logo is set, and no colors are set on company:
    #     change wizard's color according to template"""
    #     self.company.write({
    #         'primary_color': False,
    #         'secondary_color': False,
    #         'external_report_layout_id': self.layout_template1.id,
    #     })
    #     company_layout = self.report_layout1
    #     with Form(self.env['base.document.layout']) as doc_layout:
    #         self.assertColors(doc_layout, company_layout)
    #         doc_layout.report_layout_id = self.report_layout2
    #         self.assertColors(doc_layout, self.report_layout2)


@tagged('document_layout_ui')
class TestBaseDocumentLayoutUI(HttpCase):
    def test_tour(self):
        """ base document layout wizard tour """
        #TODO implementation
        pass
        # self.start_tour("URL", "test_base_document_layout", login="USER_TYPE")
