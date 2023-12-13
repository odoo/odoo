# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged, loaded_demo_data

_logger = logging.getLogger(__name__)

ATTACHMENT_DATA = [
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAEElEQVR4nGKqf3geEAAA//8EGgIyYKYzzgAAAABJRU5ErkJggg==",
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAEElEQVR4nGKqvvQEEAAA//8EBQI0GMlQsAAAAABJRU5ErkJggg==",
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAEElEQVR4nGKKLakBBAAA//8ChwFQsvFlAwAAAABJRU5ErkJggg==",
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAEElEQVR4nGJqkdoACAAA//8CfAFRzSyOUAAAAABJRU5ErkJggg==",
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAEElEQVR4nGLSfxgICAAA//8CrAFkoLBhpQAAAABJRU5ErkJggg==",
]
ATTACHMENT_COUNT = 5


@tagged('post_install', '-at_install')
class TestProductPictureController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].browse(1)
        cls.WebsiteSaleController = WebsiteSale()
        cls.product = cls.env['product.product'].create({
            'name': 'Storage Test Box',
            'standard_price': 70.0,
            'list_price': 79.0,
            'website_published': True,
        })

        cls.attachments = cls.env['ir.attachment'].create([
            {
                'datas': ATTACHMENT_DATA[i],
                'name': f'image0{i}.gif',
                'public': True
            }
            for i in range(ATTACHMENT_COUNT)])

    def _create_product_images(self):
        with MockRequest(self.product.env, website=self.website):
            self.WebsiteSaleController.add_product_images(
                [{'id': attachment.id} for attachment in self.attachments],
                self.product.id,
                self.product.product_tmpl_id.id,
            )

    def test_bulk_image_upload(self):
        # Turns attachments to product_images
        self._create_product_images()

        # Check if the media now exists on the product :
        for i, image in enumerate(self.product.product_template_image_ids):
            # Check if all names are now in the product
            self.assertIn(image.name, self.attachments.mapped('name'))
            # Check if image datas are the same
            self.assertEqual(image.image_1920, ATTACHMENT_DATA[i])
        # Check if exactly ATTACHMENT_COUNT images were saved (no dupes/misses?)
        self.assertEqual(ATTACHMENT_COUNT, len(self.product.product_template_image_ids))

    def test_image_clear(self):
        # First create some images
        self._create_product_images()
        self.assertEqual(ATTACHMENT_COUNT, len(self.product.product_template_image_ids))

        # Remove all images
        # (Exception raised if error)
        with MockRequest(self.product.env, website=self.website):
            self.WebsiteSaleController.clear_product_images(
                self.product.id,
                self.product.product_tmpl_id.id,
            )
        # According to the product, there are no variants images.
        self.assertEqual(0, len(self.product.product_template_image_ids))

    def test_extra_images_with_new_variant(self):
        # Test that adding images for a variant that is not yet created works
        product_attribute = self.env['product.attribute'].create({
            "name": "Test attribute",
            "create_variant": "dynamic",
        })
        product_attribute_values = self.env['product.attribute.value'].create([
            {
                "name" : "Test Dynamic 1",
                "attribute_id": product_attribute.id,
                "sequence": 1,
            },
            {
                "name" : "Test Dynamic 2",
                "attribute_id": product_attribute.id,
                "sequence": 2,
            }
        ])
        product_template = self.env['product.template'].create({
            "name": "test product",
            "website_published": True,
        })
        product_template_attribute_line = self.env['product.template.attribute.line'].create({
            "attribute_id": product_attribute.id,
            "product_tmpl_id": product_template.id,
            "value_ids": product_attribute_values,
        })
        self.assertEqual(0, len(product_template.product_variant_ids))
        with MockRequest(product_template.env, website=self.website):
            self.WebsiteSaleController.add_product_images(
                [{'id': self.attachments[0].id}],
                False,
                product_template.id,
                [product_template_attribute_line.product_template_value_ids[0].id],
            )
        self.assertEqual(1, len(product_template.product_variant_ids))

    def test_resequence_images(self):
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            # Test moving to first position
            images = self.product._get_images()
            data_source = images[2].image_1920
            data_target = images[0].image_1920
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name,
                images[2].id,
                'first',
            )
            images = self.product._get_images()
            self.assertEqual(images[2].image_1920, data_target)
            self.assertEqual(images[0].image_1920, data_source)
            # Test moving one to the left
            data_source = images[2].image_1920
            data_target = images[1].image_1920
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name,
                images[2].id,
                'left',
            )
            images = self.product._get_images()
            self.assertEqual(images[2].image_1920, data_target)
            self.assertEqual(images[1].image_1920, data_source)
            # Test moving one to the right
            data_source = images[2].image_1920
            data_target = images[3].image_1920
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name,
                images[2].id,
                'right',
            )
            images = self.product._get_images()
            self.assertEqual(images[2].image_1920, data_target)
            self.assertEqual(images[3].image_1920, data_source)
            # Test moving one to the last position
            data_source = images[2].image_1920
            data_target = images[-1].image_1920
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name,
                images[2].id,
                'last',
            )
            images = self.product._get_images()
            self.assertEqual(images[2].image_1920, data_target)
            self.assertEqual(images[-1].image_1920, data_source)
            # Test moving an image with a video_url instead of image_1920
            data_target = images[1].image_1920
            images[2].video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name,
                images[2].id,
                'left',
            )
            images = self.product._get_images()
            self.assertEqual(images[1].video_url, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            self.assertEqual(images[2].video_url, False)
            self.assertEqual(images[2].image_1920, data_target)
            # Test that it is not possible to move an "embedded" video to the first position
            with self.assertRaises(ValidationError):
                self.WebsiteSaleController.resequence_product_image(
                    images[1]._name,
                    images[1].id,
                    'left',
                )
            with self.assertRaises(ValidationError):
                self.WebsiteSaleController.resequence_product_image(
                    images[1]._name,
                    images[1].id,
                    'first',
                )


@tagged('post_install', '-at_install')
class TestWebsiteSaleEditor(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.users'].create({
            'name': 'Restricted Editor',
            'login': 'restricted',
            'password': 'restricted',
            'groups_id': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('sales_team.group_sale_manager').id,
                cls.env.ref('website.group_website_restricted_editor').id
            ])]
        })

    def test_category_page_and_products_snippet(self):
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        SHOP_CATEGORY_ID = 2
        self.start_tour(self.env['website'].get_client_action_url(f'/shop/category/{SHOP_CATEGORY_ID}'), 'category_page_and_products_snippet_edition', login='restricted')
        self.start_tour(f'/shop/category/{SHOP_CATEGORY_ID}', 'category_page_and_products_snippet_use', login=None)

    def test_website_sale_restricted_editor_ui(self):
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.start_tour(self.env['website'].get_client_action_url('/shop'), 'website_sale_restricted_editor_ui', login='restricted')
