# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleReorderFromPortal(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['website'].get_current_website().enabled_portal_reorder_button = True

    def test_website_sale_reorder_from_portal(self):
        product_1, product_2 = self.env['product.product'].create([
            {
                'name': 'Reorder Product 1',
                'sale_ok': True,
                'website_published': True,
            },
            {
                'name': 'Reorder Product 2',
                'sale_ok': True,
                'website_published': True,
            },
        ])
        no_variant_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'S'}),
                Command.create({'name': 'M'}),
                Command.create({'name': 'L', 'is_custom': True}),
            ]
        })
        s, _m, l = no_variant_attribute.value_ids
        no_variant_template = self.env['product.template'].create({
            'name': 'Sofa',
            'attribute_line_ids': [Command.create({
                'attribute_id': no_variant_attribute.id,
                'value_ids': [Command.set(no_variant_attribute.value_ids.ids)],
            })]
        })
        ptavs = no_variant_template.attribute_line_ids.product_template_value_ids
        ptav_s = ptavs.filtered(lambda ptav: ptav.product_attribute_value_id == s)
        ptav_l = ptavs.filtered(lambda ptav: ptav.product_attribute_value_id == l)
        user_admin = self.env.ref('base.user_admin')
        order = self.env['sale.order'].create({
            'partner_id': user_admin.partner_id.id,
            'state': 'sale',
            'order_line': [
                Command.create({
                    'product_id': product_1.id,
                }),
                Command.create({
                    'product_id': product_2.id,
                }),
                Command.create({
                    'product_id': no_variant_template.product_variant_id.id,
                    'product_no_variant_attribute_value_ids': [Command.set(ptav_s.ids)],
                }),
                Command.create({
                    'product_id': no_variant_template.product_variant_id.id,
                    'product_no_variant_attribute_value_ids': [Command.set(ptav_l.ids)],
                    'product_custom_attribute_value_ids': [Command.create({
                        'custom_product_template_attribute_value_id': ptav_l.id,
                        'custom_value': 'Whatever',
                    })]
                })
            ],
        })
        order.message_subscribe(user_admin.partner_id.ids)

        self.start_tour("/", 'website_sale_reorder_from_portal', login='admin')

        reorder_cart = self.env['sale.order'].search([('website_id', '!=', False)], limit=1)
        previous_lines = order.order_line
        order_lines = reorder_cart.order_line

        self.assertEqual(previous_lines.product_id, order_lines.product_id)
        self.assertEqual(previous_lines.mapped('name'), order_lines.mapped('name'))
        self.assertEqual(
            previous_lines.product_no_variant_attribute_value_ids,
            order_lines.product_no_variant_attribute_value_ids,
        )
