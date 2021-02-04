import os
from PIL import Image
from functools import partial

from odoo.tests import TransactionCase, tagged, Form
from odoo.tools import frozendict, image_to_base64, hex_to_rgb


dir_path = os.path.dirname(os.path.realpath(__file__))
_file_cache = {}


class TestBaseDocumentLayoutHelpers(TransactionCase):
    #
    #   Public
    #
    def setUp(self):
        super(TestBaseDocumentLayoutHelpers, self).setUp()
        self.color_fields = ['primary_color', 'secondary_color']
        self.company = self.env.company
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
    def _compare_colors_rgb(self, color1, color2):
        self.assertEqual(bool(color1), bool(color2))
        if not color1:
            return
        color1 = hex_to_rgb(color1)
        color2 = hex_to_rgb(color2)
        self.assertEqual(len(color1), len(color2))
        for i in range(len(color1)):
            self.assertAlmostEqual(color1[i], color2[i], delta=self.css_color_error)

    def _get_images_for_test(self):
        return ['sweden.png', 'odoo.png']

    def _set_images(self):
        for fname in self._get_images_for_test():
            fname_split = fname.split('.')
            if not fname_split[0] in _file_cache:
                with Image.open(os.path.join(dir_path, fname), 'r') as img:
                    base64_img = image_to_base64(img, 'PNG')
                    primary, secondary = self.env['base.document.layout'].extract_image_primary_secondary_colors(base64_img)
                    _img = frozendict({
                        'img': base64_img,
                        'colors': {
                            'primary_color': primary,
                            'secondary_color': secondary,
                        },
                    })
                    _file_cache[fname_split[0]] = _img
        self.company_imgs = frozendict(_file_cache)

    def _set_templates_and_layouts(self):
        self.layout_template1 = self.env['ir.ui.view'].create({
            'name': 'layout_template1',
            'key': 'web.layout_template1',
            'type': 'qweb',
            'arch': '''<div></div>''',
        })
        self.env['ir.model.data'].create({
            'name': self.layout_template1.name,
            'model': 'ir.ui.view',
            'module': 'web',
            'res_id': self.layout_template1.id,
        })
        self.default_colors = {
            'primary_color': '#000000',
            'secondary_color': '#000000',
        }
        self.report_layout1 = self.env['report.layout'].create({
            'view_id': self.layout_template1.id,
            'name': 'report_%s' % self.layout_template1.name,
        })
        self.layout_template2 = self.env['ir.ui.view'].create({
            'name': 'layout_template2',
            'key': 'web.layout_template2',
            'type': 'qweb',
            'arch': '''<div></div>''',
        })
        self.env['ir.model.data'].create({
            'name': self.layout_template2.name,
            'model': 'ir.ui.view',
            'module': 'web',
            'res_id': self.layout_template2.id,
        })
        self.report_layout2 = self.env['report.layout'].create({
            'view_id': self.layout_template2.id,
            'name': 'report_%s' % self.layout_template2.name,
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
            'external_report_layout_id': self.env.ref('web.layout_template1').id,
            'paperformat_id': self.env.ref('base.paperformat_us').id,
        })
        default_colors = self.default_colors
        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, default_colors)
            self.assertEqual(doc_layout.company_id, self.company)
            doc_layout.logo = self.company_imgs['sweden']['img']

            self.assertColors(doc_layout, self.company_imgs['sweden']['colors'])

            doc_layout.logo = ''
            self.assertColors(doc_layout, self.company_imgs['sweden']['colors'])
            self.assertEqual(doc_layout.logo, '')

    def test_company_no_color_but_logo_change_logo(self):
        """When company colors are not set, but a logo is,
        the wizard displays the computed colors from the logo"""
        self.company.write({
            'primary_color': '#ff0080',
            'secondary_color': '#00ff00',
            'logo': self.company_imgs['sweden']['img'],
            'paperformat_id': self.env.ref('base.paperformat_us').id,
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['odoo']['img']
            self.assertColors(doc_layout, self.company_imgs['odoo']['colors'])

    def test_company_colors_change_logo(self):
        """changes of the logo implies displaying the new computed colors"""
        self.company.write({
            'primary_color': '#ff0080',
            'secondary_color': '#00ff00',
            'logo': False,
            'paperformat_id': self.env.ref('base.paperformat_us').id,
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['odoo']['img']
            self.assertColors(doc_layout, self.company_imgs['odoo']['colors'])

    def test_company_colors_and_logo_change_logo(self):
        """The colors of the company may differ from the one the logo computes
        Opening the wizard in these condition displays the company's colors
        When the logo changes, colors must change according to the logo"""
        self.company.write({
            'primary_color': '#ff0080',
            'secondary_color': '#00ff00',
            'logo': self.company_imgs['sweden']['img'],
            'paperformat_id': self.env.ref('base.paperformat_us').id,
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.logo = self.company_imgs['odoo']['img']
            self.assertColors(doc_layout, self.company_imgs['odoo']['colors'])

    # Layout change tests
    def test_company_colors_reset_colors(self):
        """Reset the colors when they differ from the ones originally
        computed from the company logo"""
        self.company.write({
            'primary_color': '#ff0080',
            'secondary_color': '#00ff00',
            'logo': self.company_imgs['sweden']['img'],
            'paperformat_id': self.env.ref('base.paperformat_us').id,
        })

        with Form(self.env['base.document.layout']) as doc_layout:
            self.assertColors(doc_layout, self.company)
            doc_layout.primary_color = doc_layout.logo_primary_color
            doc_layout.secondary_color = doc_layout.logo_secondary_color
            self.assertColors(doc_layout, self.company_imgs['sweden']['colors'])

    def test_parse_company_colors_grayscale(self):
        """Grayscale images with transparency - make sure the color extraction does not crash"""
        self.company.write({
            'primary_color': '#ff0080',
            'secondary_color': '#00ff00',
            'paperformat_id': self.env.ref('base.paperformat_us').id,
        })
        with Form(self.env['base.document.layout']) as doc_layout:
            with Image.open(os.path.join(dir_path, 'logo_ci.png'), 'r') as img:
                base64_img = image_to_base64(img, 'PNG')
                doc_layout.logo = base64_img
            self.assertNotEqual(None, doc_layout.primary_color)


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
    #     default_colors = self.default_colors
    #     with Form(self.env['base.document.layout']) as doc_layout:
    #         self.assertColors(doc_layout, default_colors)
    #         doc_layout.report_layout_id = self.report_layout2
    #         self.assertColors(doc_layout, self.report_layout2)
