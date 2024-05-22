# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from odoo.addons.website_sale.tests.common import TestWebsiteSaleCommon
from PIL import Image

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteSaleImage(odoo.tests.HttpCase, TestWebsiteSaleCommon):

    # registry_test_mode = False  # uncomment to save the product to test in browser

    def test_01_admin_shop_zoom_tour(self):
        color_red = '#CD5C5C'
        name_red = 'Indian Red'

        color_green = '#228B22'
        name_green = 'Forest Green'

        color_blue = '#4169E1'
        name_blue = 'Royal Blue'

        # create the color attribute
        product_attribute = self.env['product.attribute'].create({
            'name': 'Beautiful Color',
            'display_type': 'color',
        })

        # create the color attribute values
        attr_values = self.env['product.attribute.value'].create([{
            'name': name_red,
            'attribute_id': product_attribute.id,
            'html_color': color_red,
            'sequence': 1,
        }, {
            'name': name_green,
            'attribute_id': product_attribute.id,
            'html_color': color_green,
            'sequence': 2,
        }, {
            'name': name_blue,
            'attribute_id': product_attribute.id,
            'html_color': color_blue,
            'sequence': 3,
        }])

        # first image (blue) for the template
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), color_blue).save(f, 'JPEG')
        f.seek(0)
        blue_image = base64.b64encode(f.read())

        # second image (red) for the variant 1, small image (no zoom)
        f = io.BytesIO()
        Image.new('RGB', (800, 500), color_red).save(f, 'JPEG')
        f.seek(0)
        red_image = base64.b64encode(f.read())

        # second image (green) for the variant 2, big image (zoom)
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), color_green).save(f, 'JPEG')
        f.seek(0)
        green_image = base64.b64encode(f.read())

        # Template Extra Image 1
        f = io.BytesIO()
        Image.new('RGB', (124, 147)).save(f, 'GIF')
        f.seek(0)
        image_gif = base64.b64encode(f.read())

        # Template Extra Image 2
        image_svg = base64.b64encode(b'<svg></svg>')

        # Red Variant Extra Image 1
        f = io.BytesIO()
        Image.new('RGB', (767, 247)).save(f, 'BMP')
        f.seek(0)
        image_bmp = base64.b64encode(f.read())

        # Green Variant Extra Image 1
        f = io.BytesIO()
        Image.new('RGB', (2147, 3251)).save(f, 'PNG')
        f.seek(0)
        image_png = base64.b64encode(f.read())

        # create the template, without creating the variants
        template = self.env['product.template'].with_context(create_product_product=True).create({
            'name': 'A Colorful Image',
            'product_template_image_ids': [(0, 0, {'name': 'image 1', 'image_1920': image_gif}), (0, 0, {'name': 'image 4', 'image_1920': image_svg})],
        })

        # set the color attribute and values on the template
        line = self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': template.id,
            'value_ids': [(6, 0, attr_values.ids)]
        }])
        value_red = line.product_template_value_ids[0]
        value_green = line.product_template_value_ids[1]

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=', template.id)])

        for val in product_template_attribute_values:
            if val.name == name_red:
                val.price_extra = 10
            else:
                val.price_extra = 20

        # Get RED variant, and set image to blue (will be set on the template
        # because the template image is empty and there is only one variant)
        product_red = template._get_variant_for_combination(value_red)
        product_red.write({
            'image_1920': blue_image,
            'product_variant_image_ids': [(0, 0, {'name': 'image 2', 'image_1920': image_bmp})],
        })

        self.assertEqual(template.image_1920, blue_image)

        # Get the green variant
        product_green = template._get_variant_for_combination(value_green)
        product_green.write({
            'image_1920': green_image,
            'product_variant_image_ids': [(0, 0, {'name': 'image 3', 'image_1920': image_png})],
        })

        # now set the red image on the first variant, that works because
        # template image is not empty anymore and we have a second variant
        product_red.image_1920 = red_image

        # Verify image_1920 size > 1024 can be zoomed
        self.assertTrue(template.can_image_1024_be_zoomed)
        self.assertFalse(template.product_template_image_ids[0].can_image_1024_be_zoomed)
        self.assertFalse(template.product_template_image_ids[1].can_image_1024_be_zoomed)
        self.assertFalse(product_red.can_image_1024_be_zoomed)
        self.assertFalse(product_red.product_variant_image_ids[0].can_image_1024_be_zoomed)
        self.assertTrue(product_green.can_image_1024_be_zoomed)
        self.assertTrue(product_green.product_variant_image_ids[0].can_image_1024_be_zoomed)

        # jpeg encoding is changing the color a bit
        jpeg_blue = (65, 105, 227)
        jpeg_red = (205, 93, 92)
        jpeg_green = (34, 139, 34)

        # Verify original size: keep original
        image = Image.open(io.BytesIO(base64.b64decode(template.image_1920)))
        self.assertEqual(image.size, (1920, 1080))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = Image.open(io.BytesIO(base64.b64decode(product_red.image_1920)))
        self.assertEqual(image.size, (800, 500))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = Image.open(io.BytesIO(base64.b64decode(product_green.image_1920)))
        self.assertEqual(image.size, (1920, 1080))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green")

        # Verify 1024 size: keep aspect ratio
        image = Image.open(io.BytesIO(base64.b64decode(template.image_1024)))
        self.assertEqual(image.size, (1024, 576))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = Image.open(io.BytesIO(base64.b64decode(product_red.image_1024)))
        self.assertEqual(image.size, (800, 500))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = Image.open(io.BytesIO(base64.b64decode(product_green.image_1024)))
        self.assertEqual(image.size, (1024, 576))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green")

        # Verify 512 size: keep aspect ratio
        image = Image.open(io.BytesIO(base64.b64decode(template.image_512)))
        self.assertEqual(image.size, (512, 288))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = Image.open(io.BytesIO(base64.b64decode(product_red.image_512)))
        self.assertEqual(image.size, (512, 320))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = Image.open(io.BytesIO(base64.b64decode(product_green.image_512)))
        self.assertEqual(image.size, (512, 288))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green")

        # Verify 256 size: keep aspect ratio
        image = Image.open(io.BytesIO(base64.b64decode(template.image_256)))
        self.assertEqual(image.size, (256, 144))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = Image.open(io.BytesIO(base64.b64decode(product_red.image_256)))
        self.assertEqual(image.size, (256, 160))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = Image.open(io.BytesIO(base64.b64decode(product_green.image_256)))
        self.assertEqual(image.size, (256, 144))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green")

        # Verify 128 size: keep aspect ratio
        image = Image.open(io.BytesIO(base64.b64decode(template.image_128)))
        self.assertEqual(image.size, (128, 72))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_blue, "blue")
        image = Image.open(io.BytesIO(base64.b64decode(product_red.image_128)))
        self.assertEqual(image.size, (128, 80))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_red, "red")
        image = Image.open(io.BytesIO(base64.b64decode(product_green.image_128)))
        self.assertEqual(image.size, (128, 72))
        self.assertEqual(image.getpixel((image.size[0] / 2, image.size[1] / 2)), jpeg_green, "green")

        # self.env.cr.commit()  # uncomment to save the product to test in browser

        self.start_tour("/", 'shop_zoom', login="admin")

        # CASE: unlink move image to fallback if fallback image empty
        template.image_1920 = False
        product_red.unlink()
        self.assertEqual(template.image_1920, red_image)

        # CASE: unlink does nothing special if fallback image already set
        self.env['product.product'].create({
            'product_tmpl_id': template.id,
            'image_1920': green_image,
        }).unlink()
        self.assertEqual(template.image_1920, red_image)

        # CASE: display variant image first if set
        self.assertEqual(product_green._get_images()[0].image_1920, green_image)

        # CASE: display variant fallback after variant o2m, correct fallback
        # write on the variant field, otherwise it will write on the fallback
        product_green.image_variant_1920 = False
        images = product_green._get_images()
        # images on fields are resized to max 1920
        image = Image.open(io.BytesIO(base64.b64decode(images[0].image_1920)))
        self.assertEqual(image.size, (1268, 1920))
        self.assertEqual(images[1].image_1920, red_image)
        self.assertEqual(images[2].image_1920, image_gif)
        self.assertEqual(images[3].image_1920, image_svg)

        # CASE: When uploading a product variant image
        # we don't want the default_product_tmpl_id from the context to be applied if we have a product_variant_id set
        # we want the default_product_tmpl_id from the context to be applied if we don't have a product_variant_id set

        additionnal_context = {'default_product_tmpl_id': template.id}

        product = self.env['product.product'].create({
            'product_tmpl_id': template.id,
        })

        product_image = self.env['product.image'].with_context(**additionnal_context).create([{
            'name': 'Template image',
            'image_1920': red_image,
        }, {
            'name': 'Variant image',
            'image_1920': blue_image,
            'product_variant_id': product.id,
        }])

        template_image = product_image.filtered(lambda i: i.name == 'Template image')
        variant_image = product_image.filtered(lambda i: i.name == 'Variant image')

        self.assertEqual(template_image.product_tmpl_id.id, template.id)
        self.assertFalse(template_image.product_variant_id.id)
        self.assertFalse(variant_image.product_tmpl_id.id)
        self.assertEqual(variant_image.product_variant_id.id, product.id)

    def test_02_image_holder(self):
        f = io.BytesIO()
        Image.new('RGB', (800, 500), '#FF0000').save(f, 'JPEG')
        f.seek(0)
        image = base64.b64encode(f.read())

        # create the color attribute
        product_attribute = self.env['product.attribute'].create({
            'name': 'Beautiful Color',
            'display_type': 'color',
        })

        # create the color attribute values
        attr_values = self.env['product.attribute.value'].create([{
            'name': 'Red',
            'attribute_id': product_attribute.id,
            'sequence': 1,
        }, {
            'name': 'Green',
            'attribute_id': product_attribute.id,
            'sequence': 2,
        }, {
            'name': 'Blue',
            'attribute_id': product_attribute.id,
            'sequence': 3,
        }])

        # create the template, without creating the variants
        template = self.env['product.template'].with_context(create_product_product=True).create({
            'name': 'Test subject',
        })

        # when there are no variants, the image must be obtained from the template
        self.assertEqual(template, template._get_image_holder())

        # set the color attribute and values on the template
        line = self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': template.id,
            'value_ids': [(6, 0, attr_values.ids)]
        }])
        value_red = line.product_template_value_ids[0]
        product_red = template._get_variant_for_combination(value_red)
        product_red.image_variant_1920 = image

        value_green = line.product_template_value_ids[1]
        product_green = template._get_variant_for_combination(value_green)
        product_green.image_variant_1920 = image

        # when there are no template image but there are variants, the image must be obtained from the first variant
        self.assertEqual(product_red, template._get_image_holder())

        product_red.toggle_active()

        # but when some variants are not available, the image must be obtained from the first available variant
        self.assertEqual(product_green, template._get_image_holder())

        template.image_1920 = image

        # when there is a template image, the image must be obtained from the template
        self.assertEqual(template, template._get_image_holder())
