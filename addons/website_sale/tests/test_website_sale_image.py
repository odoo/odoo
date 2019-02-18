# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from PIL import Image

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteSaleZoom(odoo.tests.HttpCase):

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
            'type': 'color',
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
        Image.new('RGB', (1920, 1080), color_blue).save(f, 'PNG')
        f.seek(0)
        blue_image = base64.b64encode(f.read())

        # second image (red) for the variant 1, small image (no zoom)
        f = io.BytesIO()
        Image.new('RGB', (800, 500), color_red).save(f, 'PNG')
        f.seek(0)
        red_image = base64.b64encode(f.read())

        # second image (green) for the variant 2, big image (zoom)
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), color_green).save(f, 'PNG')
        f.seek(0)
        green_image = base64.b64encode(f.read())

        # create the first product and the template.
        # Set image to blue (will be set on the template because it was empty)
        product_red = self.env['product.product'].create({
            'name': 'A Colorful Image',
            'image': blue_image,
            'attribute_value_ids': [(6, 0, attr_values.filtered(lambda l: l.name == name_red).ids)],
        })

        # now set the red image on the first variant
        # that works because template image is not empty anymore
        product_red.image = red_image

        # set the color attribute and values on the template
        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_red.product_tmpl_id.id,
            'value_ids': [(6, 0, attr_values.ids)]
        }])

        # create the green variant
        self.env['product.product'].create({
            'image': green_image,
            'product_tmpl_id': product_red.product_tmpl_id.id,
            'attribute_value_ids': [(6, 0, attr_values.filtered(lambda l: l.name == name_green).ids)],
        })

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=', product_red.product_tmpl_id.id)])

        for val in product_template_attribute_values:
            if val.name == name_red:
                val.price_extra = 10
            else:
                val.price_extra = 20

        # self.env.cr.commit()  # uncomment to save the product to test in browser

        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop_zoom')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop_zoom.ready", login="admin")
