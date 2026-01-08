# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.sale_gelato.tests.common import GelatoCommon


@tagged('post_install', '-at_install')
class TestProductTemplate(GelatoCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gelato_template.gelato_template_ref = 'dummy_ref'
        cls.gelato_template._create_print_images_from_gelato_info(cls.template_data_one_variant)

    def test_prevent_publishing_product_without_print_images(self):
        with self.assertRaises(ValidationError):
            self.gelato_template.is_published = True

    def test_prevent_removing_print_images_from_published_product(self):
        self.gelato_template.gelato_image_ids[0].datas = 'test'
        self.gelato_template.gelato_image_ids[1].datas = 'test'

        self.write = self.gelato_template.is_published = True

        with self.assertRaises(ValidationError):
            self.gelato_template.gelato_image_ids[1].datas = ''
