# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged

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

    def _get_product_image_data(self):
        return [
            hasattr(image, 'video_url') and image.video_url or image.image_1920
            for image in self.product._get_images()
        ]

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

    def test_resequence_image_first(self):
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            images = self.product._get_images()
            i1, i2, i3, i4, i5, i6 = self._get_product_image_data()
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name, images[2].id, 'first',
            )
            # Trigger the reordering of product.image records based on their sequence.
            self.env['product.image'].invalidate_model()
            self.assertListEqual(self._get_product_image_data(), [i3, i1, i2, i4, i5, i6])
            self.assertEqual(self.product.image_1920, i3)

    def test_resequence_image_left(self):
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            images = self.product._get_images()
            i1, i2, i3, i4, i5, i6 = self._get_product_image_data()
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name, images[2].id, 'left',
            )
            self.env['product.image'].invalidate_model()
            self.assertListEqual(self._get_product_image_data(), [i1, i3, i2, i4, i5, i6])

    def test_resequence_image_right(self):
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            images = self.product._get_images()
            i1, i2, i3, i4, i5, i6 = self._get_product_image_data()
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name, images[2].id, 'right',
            )
            self.env['product.image'].invalidate_model()
            self.assertListEqual(self._get_product_image_data(), [i1, i2, i4, i3, i5, i6])

    def test_resequence_image_last(self):
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            images = self.product._get_images()
            i1, i2, i3, i4, i5, i6 = self._get_product_image_data()
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name, images[2].id, 'last',
            )
            self.env['product.image'].invalidate_model()
            self.assertListEqual(self._get_product_image_data(), [i1, i2, i4, i5, i6, i3])

    def test_resequence_image_first_to_last(self):
        """ Moving an image from first to last position is an edge case in the code. """
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            images = self.product._get_images()
            i1, i2, i3, i4, i5, i6 = self._get_product_image_data()
            self.WebsiteSaleController.resequence_product_image(
                images[0]._name, images[0].id, 'last',
            )
            self.env['product.image'].invalidate_model()
            self.assertListEqual(self._get_product_image_data(), [i2, i3, i4, i5, i6, i1])
            self.assertEqual(self.product.image_1920, i2)

    def test_resequence_video_left(self):
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            images = self.product._get_images()
            images[2].video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            i1, i2, i3, i4, i5, i6 = self._get_product_image_data()
            self.WebsiteSaleController.resequence_product_image(
                images[2]._name, images[2].id, 'left',
            )
            self.env['product.image'].invalidate_model()
            self.assertListEqual(self._get_product_image_data(), [i1, i3, i2, i4, i5, i6])

    def test_resequence_video_first(self):
        """ A video can't be resequenced to first position. """
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            images = self.product._get_images()
            images[2].video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            i1, i2, i3, i4, i5, i6 = self._get_product_image_data()
            with self.assertRaises(ValidationError):
                self.WebsiteSaleController.resequence_product_image(
                    images[2]._name, images[2].id, 'first',
                )
            self.env['product.image'].invalidate_model()
            self.assertListEqual(self._get_product_image_data(), [i1, i2, i3, i4, i5, i6])

    def test_resequence_video_replace_first(self):
        """ A video can't replace an image that was resequenced away from first position. """
        self._create_product_images()
        with MockRequest(self.product.env, website=self.website):
            images = self.product._get_images()
            images[1].video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            i1, i2, i3, i4, i5, i6 = self._get_product_image_data()
            with self.assertRaises(ValidationError):
                self.WebsiteSaleController.resequence_product_image(
                    images[0]._name, images[0].id, 'right',
                )
            self.env['product.image'].invalidate_model()
            self.assertListEqual(self._get_product_image_data(), [i1, i2, i3, i4, i5, i6])


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
        category = self.env['product.public.category'].create({
            'name': 'Test Category',
        })
        self.env['product.template'].create({
            'name': 'Test Product',
            'website_published': True,
            'public_categ_ids': [
                Command.link(category.id)
            ]
        })
        self.env['product.template'].create({
            'name': 'Test Product Outside Category',
            'website_published': True,
        })
        self.start_tour(self.env['website'].get_client_action_url('/shop'), 'category_page_and_products_snippet_edition', login='restricted')
        self.start_tour('/shop', 'category_page_and_products_snippet_use', login=None)

    def test_website_sale_restricted_editor_ui(self):
        self.env['product.template'].create({
            'name': 'Test Product',
            'website_sequence': 0,
            'website_published': True,
        })
        self.start_tour(self.env['website'].get_client_action_url('/shop'), 'website_sale_restricted_editor_ui', login='restricted')
