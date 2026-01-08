# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from PIL import Image

from odoo.fields import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes
from odoo.tools.image import binary_to_image

from odoo.addons.website.tests.common import HttpCaseWithWebsiteUser


def _create_image(color="black", dims=(1920, 1080), format="JPEG"):
    f = io.BytesIO()
    Image.new("RGB", dims, color).save(f, format)  # type: ignore
    f.seek(0)
    return BinaryBytes(f.read())


@tagged("post_install", "-at_install")
class TestWebsiteSaleImage(HttpCaseWithWebsiteUser):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        color_red = "#CD5C5C"
        name_red = "Indian Red"

        color_green = "#228B22"
        name_green = "Forest Green"

        color_blue = "#4169E1"
        name_blue = "Royal Blue"

        # create the color attribute
        cls.product_attribute = cls.env["product.attribute"].create({
            "name": "Beautiful Color",
            "display_type": "color",
            "value_ids": [
                Command.create({"name": name_red, "html_color": color_red, "sequence": 1}),
                Command.create({"name": name_green, "html_color": color_green, "sequence": 2}),
                Command.create({"name": name_blue, "html_color": color_blue, "sequence": 3}),
            ],
        })

        cls.blue_image = _create_image(color=color_blue)
        cls.red_image = _create_image(color=color_red, dims=(800, 500))
        cls.green_image = _create_image(color=color_green)

        cls.template = cls.env["product.template"].create({
            "name": "A Colorful Image",
            "attribute_line_ids": [
                Command.create({
                    "attribute_id": cls.product_attribute.id,
                    "value_ids": [Command.set(cls.product_attribute.value_ids.ids)],
                })
            ],
            "image_1920": cls.blue_image,
        })

        line = cls.template.attribute_line_ids
        cls.value_red = line.product_template_value_ids[0]
        cls.value_green = line.product_template_value_ids[1]
        cls.value_blue = line.product_template_value_ids[2]

        cls.product_red = cls.template._get_variant_for_combination(cls.value_red)
        cls.product_green = cls.template._get_variant_for_combination(cls.value_green)
        cls.product_blue = cls.template._get_variant_for_combination(cls.value_blue)

    def test_01_admin_shop_zoom_tour(self):
        self.env["product.pricelist"].sudo().search([]).action_archive()

        # Template Extra Image 1
        image_gif = _create_image(dims=(124, 147), format="GIF")

        # Template Extra Image 2
        image_svg = BinaryBytes(b"<svg></svg>")

        # Red Variant Extra Image 1
        image_bmp = _create_image(dims=(767, 247), format="BMP")

        # Green Variant Extra Image 1
        image_png = _create_image(dims=(2147, 3251), format="PNG")

        # create the template, without creating the variants
        self.template.write({
            "product_template_image_ids": [
                Command.create({"name": "image 1", "image_1920": image_gif}),
                Command.create({"name": "image 4", "image_1920": image_svg}),
            ]
        })

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env["product.template.attribute.value"].search([
            ("product_tmpl_id", "=", self.template.id)
        ])

        for val in product_template_attribute_values:
            if val.name == "Indian Red":
                val.price_extra = 10
            else:
                val.price_extra = 20

        # Set image to blue for red variant
        self.product_red.write({
            "image_1920": self.blue_image,
            "product_template_image_ids": [
                Command.create({
                    "name": "image 2",
                    "image_1920": image_bmp,
                    "attribute_value_ids": [Command.link(self.value_red.id)],
                })
            ],
        })

        self.assertEqual(self.template.image_1920.content, self.blue_image.content)

        # Set image to green for green variant
        self.product_green.write({
            "image_1920": self.green_image,
            "product_template_image_ids": [
                Command.create({
                    "name": "image 3",
                    "image_1920": image_png,
                    "attribute_value_ids": [Command.link(self.value_green.id)],
                })
            ],
        })

        # now set the red image on the first variant, that works because
        # template image is not empty anymore and we have a second variant
        self.product_red.image_1920 = self.red_image

        # Verify image_1920 size > 1024 can be zoomed
        self.assertTrue(self.template.can_image_1024_be_zoomed)
        self.assertFalse(self.template.product_template_image_ids[0].can_image_1024_be_zoomed)
        self.assertFalse(self.template.product_template_image_ids[1].can_image_1024_be_zoomed)
        self.assertFalse(self.product_red.can_image_1024_be_zoomed)
        self.assertFalse(
            self.product_red.variant_image_ids.filtered(lambda img: img.attribute_value_ids)[
                0
            ].can_image_1024_be_zoomed
        )
        self.assertTrue(self.product_green.can_image_1024_be_zoomed)
        self.assertTrue(
            self.product_green.variant_image_ids.filtered(lambda img: img.attribute_value_ids)[
                0
            ].can_image_1024_be_zoomed
        )

        # jpeg encoding is changing the color a bit
        jpeg_blue = (65, 105, 227)
        jpeg_red = (205, 93, 92)
        jpeg_green = (34, 139, 34)

        # Verify original size: keep original
        image = binary_to_image(self.template.image_1920)
        self.assertEqual(image.size, (1920, 1080))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = binary_to_image(self.product_red.image_1920)
        self.assertEqual(image.size, (800, 500))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = binary_to_image(self.product_green.image_1920)
        self.assertEqual(image.size, (1920, 1080))
        self.assertEqual(
            image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green"
        )

        # Verify 1024 size: keep aspect ratio
        image = binary_to_image(self.template.image_1024)
        self.assertEqual(image.size, (1024, 576))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = binary_to_image(self.product_red.image_1024)
        self.assertEqual(image.size, (800, 500))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = binary_to_image(self.product_green.image_1024)
        self.assertEqual(image.size, (1024, 576))
        self.assertEqual(
            image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green"
        )

        # Verify 512 size: keep aspect ratio
        image = binary_to_image(self.template.image_512)
        self.assertEqual(image.size, (512, 288))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = binary_to_image(self.product_red.image_512)
        self.assertEqual(image.size, (512, 320))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = binary_to_image(self.product_green.image_512)
        self.assertEqual(image.size, (512, 288))
        self.assertEqual(
            image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green"
        )

        # Verify 256 size: keep aspect ratio
        image = binary_to_image(self.template.image_256)
        self.assertEqual(image.size, (256, 144))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = binary_to_image(self.product_red.image_256)
        self.assertEqual(image.size, (256, 160))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = binary_to_image(self.product_green.image_256)
        self.assertEqual(image.size, (256, 144))
        self.assertEqual(
            image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green"
        )

        # Verify 128 size: keep aspect ratio
        image = binary_to_image(self.template.image_128)
        self.assertEqual(image.size, (128, 72))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = binary_to_image(self.product_red.image_128)
        self.assertEqual(image.size, (128, 80))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = binary_to_image(self.product_green.image_128)
        self.assertEqual(image.size, (128, 72))
        self.assertEqual(
            image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green"
        )

        # self.env.cr.commit()  # uncomment to save the product to test in browser

        # Make sure we have zoom on click
        self.env["ir.ui.view"].with_context(active_test=False).search([
            ("key", "=", "website_sale.product_picture_magnify_click")
        ]).write({"active": True})

        # Ensure that no pricelist is available during the test.
        # This ensures that tours with triggers on the amounts will run properly.
        self.env["product.pricelist"].search([]).action_archive()

        self.start_tour(
            "/shop?debug=1&search=A Colorful Image",
            "website_sale.product_page_zoom",
            login="website_user",
        )

        # CASE: If the template image is removed, the first image without attribute values from
        # product_template_image_ids is used as fallback
        self.template.image_1920 = False
        self.assertEqual(
            self.template.image_1920.content,
            self.template.product_template_image_ids.filtered(
                lambda image: not image.attribute_value_ids
            )[0].image_1920.content,
        )

        # CASE: unlink does nothing special if fallback image already set
        self.env["product.product"].create({
            "product_tmpl_id": self.template.id,
            "image_1920": self.green_image,
        }).unlink()
        self.assertEqual(
            self.template.image_1920.content,
            self.template.product_template_image_ids.filtered(
                lambda image: not image.attribute_value_ids
            )[0].image_1920.content,
        )

        # CASE: display variant image first if set
        self.assertEqual(
            self.product_green._get_images()[0].image_1920.content, self.green_image.content
        )

        # CASE: display variant fallback after variant o2m, correct fallback
        # write on the variant field, otherwise it will write on the fallback
        self.product_green.image_variant_1920 = False
        images = self.product_green._get_images()
        # images on fields are resized to max 1920
        image_png = binary_to_image(images[1].image_1920)
        self.assertEqual(images[0].image_1920.content, image_gif.content)
        self.assertEqual(image_png.size, (1268, 1920))
        self.assertEqual(images[2].image_1920.content, image_gif.content)
        self.assertEqual(images[3].image_1920.content, image_svg.content)

    def test_02_image_holder(self):
        image = _create_image(color="#FF0000", dims=(800, 500))

        # create the template, without creating the variants
        template = (
            self
            .env["product.template"]
            .with_context(create_product_product=False)
            .create({"name": "Test subject"})
        )

        # when there are no variants, the image must be obtained from the template
        self.assertEqual(template, template._get_image_holder())

        # set the color attribute and values on the template
        line = self.env["product.template.attribute.line"].create([
            {
                "attribute_id": self.product_attribute.id,
                "product_tmpl_id": template.id,
                "value_ids": [Command.set(self.product_attribute.value_ids.ids)],
            }
        ])
        value_red = line.product_template_value_ids[0]
        product_red = template._get_variant_for_combination(value_red)
        product_red.image_variant_1920 = image

        value_green = line.product_template_value_ids[1]
        product_green = template._get_variant_for_combination(value_green)
        product_green.image_variant_1920 = image

        # when there are no template image but there are variants, the image must be obtained from
        # the first variant
        self.assertEqual(product_red, template._get_image_holder())

        product_red.action_archive()

        # but when some variants are not available, the image must be obtained from the first
        # available variant
        self.assertEqual(product_green, template._get_image_holder())

        template.image_1920 = image

        # when there is a template image, the image must be obtained from the template
        self.assertEqual(template, template._get_image_holder())

    def test_03_assign_image_to_variants(self):
        self.template.write({
            "product_template_image_ids": [
                Command.create({
                    "name": "green",
                    "image_1920": self.green_image,
                    "attribute_value_ids": [Command.set([self.value_green.id, self.value_blue.id])],
                })
            ]
        })

        self.assertEqual(
            self.product_green.variant_image_ids[0].image_1920.content, self.green_image.content
        )

        self.assertEqual(
            self.product_blue.variant_image_ids[0].image_1920.content, self.green_image.content
        )

    def test_04_remove_main_image_fallback_to_extra_image(self):
        self.template.write({
            "product_template_image_ids": [
                Command.create({"name": "green", "image_1920": self.green_image})
            ]
        })

        self.template.image_1920 = False

        self.assertEqual(self.template.image_1920.content, self.green_image.content)

        # If we remove the main image which is same as first extra image then it will remove extra
        # image also.
        self.template.image_1920 = False
        self.assertFalse(self.template.product_template_image_ids)

    def test_05_remove_main_image_fallback_to_variant_extra_image(self):
        self.template.write({
            "product_template_image_ids": [
                Command.create({
                    "name": "red",
                    "image_1920": self.red_image,
                    "attribute_value_ids": [Command.link(self.value_red.id)],
                })
            ]
        })
        self.template.image_1920 = False

        self.assertEqual(self.template.image_1920.content, self.red_image.content)

    def test_06_remove_main_variant_image_fallback_to_extra_image(self):
        self.product_red.image_1920 = self.green_image

        self.product_red.write({
            "product_template_image_ids": [
                Command.create({
                    "name": "red",
                    "image_1920": self.red_image,
                    "attribute_value_ids": [Command.link(self.value_red.id)],
                })
            ]
        })

        self.product_red.image_1920 = False

        self.assertEqual(self.product_red.image_1920.content, self.red_image.content)


@tagged("post_install", "-at_install")
class TestWebsiteSaleRemoveImage(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # First image (blue) for the template.
        color_blue = "#4169E1"
        name_blue = "Royal Blue"
        # Red for the variant.
        color_red = "#CD5C5C"
        name_red = "Indian Red"
        # Green for the replacement
        color_green = "#228B22"

        # Attachment needed for the replacement of images
        cls.env["ir.attachment"].create({
            "public": True,
            "name": "green.jpg",
            "type": "binary",
            "raw": _create_image(color=color_green),
        })

        # Create the color attribute.
        cls.product_attribute = cls.env["product.attribute"].create({
            "name": "Beautiful Color",
            "display_type": "color",
        })

        # create the color attribute values
        cls.attr_values = cls.env["product.attribute.value"].create([
            {
                "name": name_blue,
                "attribute_id": cls.product_attribute.id,
                "html_color": color_blue,
                "sequence": 1,
            },
            {
                "name": name_red,
                "attribute_id": cls.product_attribute.id,
                "html_color": color_red,
                "sequence": 2,
            },
        ])

        cls.template = (
            cls
            .env["product.template"]
            .with_context(create_product_product=False)
            .create({"name": "Test Remove Image", "image_1920": _create_image(color=color_blue)})
        )

    def test_website_sale_add_and_remove_main_product_image_no_variant(self):
        self.product = self.env["product.product"].create({"product_tmpl_id": self.template.id})

        self.start_tour(
            self.env["website"].get_client_action_url("/shop?search=Test Remove Image"),
            "website_sale.add_and_remove_main_product_image_no_variant",
            login="admin",
        )
        self.assertFalse(self.template.image_1920)
        self.assertFalse(self.product.image_1920)

    def test_website_sale_remove_main_product_image_with_variant(self):
        # Set the color attribute and values on the template.
        self.env["product.template.attribute.line"].create([
            {
                "attribute_id": self.product_attribute.id,
                "product_tmpl_id": self.template.id,
                "value_ids": [(6, 0, self.attr_values.ids)],
            }
        ])
        self.product = self.env["product.product"].create({"product_tmpl_id": self.template.id})
        self.start_tour(
            self.env["website"].get_client_action_url("/shop?search=Test Remove Image"),
            "website_sale.remove_main_product_image_with_variant",
            login="admin",
        )
        self.assertFalse(self.template.image_1920)
        self.assertFalse(self.product.image_1920)
