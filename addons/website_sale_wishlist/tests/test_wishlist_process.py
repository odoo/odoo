# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestWishlistProcess(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['product.template'].search([]).write({'website_published': False})
        cls.env['res.config.settings'].create({'group_product_variant': True}).execute()

    def test_wishlist_ui(self):
        # Setup attributes and attributes values
        attributes = self.env['product.attribute'].create([
            {
                'name': 'Legs',
                'sequence': 10,
                'value_ids': [
                    Command.create({
                        'name': 'Steel',
                        'sequence': 1,
                    }),
                    Command.create({
                        'name': 'Aluminium',
                        'sequence': 2,
                    }),
                ],
            }, {
                'name': 'Color',
                'sequence': 20,
                'value_ids': [
                    Command.create({
                        'name': 'White',
                        'sequence': 1,
                    }),
                    Command.create({
                        'name': 'Black',
                        'sequence': 2,
                    }),
                ],
            },
        ])

        # Create product template
        self.env['product.template'].create({
            'name': 'Customizable Desk (TEST)',
            'standard_price': 500.0,
            'list_price': 750.0,
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [Command.set(attribute.value_ids.ids)]
                }) for attribute in attributes
            ],
        })

        self.env.ref('base.user_admin').name = 'Mitchell Admin'

        self.start_tour('/', 'website_sale_wishlist.wishlist_updates', timeout=120)

    def test_wishlist_dynamic_attributes(self):

        dynamic_color = self.env['product.attribute'].create({
            'name': "color",
            'display_type': 'color',
            'create_variant': 'dynamic',
            'value_ids': [
                Command.create({'name': 'red'}),
                Command.create({'name': 'blue'}),
                Command.create({'name': 'black'}),
            ]
        })
        bottle = self.env['product.template'].create({
            'name': "Bottle",
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': dynamic_color.id,
                    'value_ids': [Command.set(dynamic_color.value_ids.ids)]
                })
            ],
            'website_published': True,
        })
        self.start_tour("/", 'website_sale_wishlist.dynamic_variants')
        bottle.product_variant_ids[:1].action_archive()
        self.start_tour("/", 'website_sale_wishlist.archived_variant')
        bottle.product_variant_ids.action_archive()
        # Republish the template after archiving all variants so the product
        # page stays reachable.
        # The with_context(active_test=False) write flips the template back to
        # active=True and website_published=True, countering the new
        # WebsitePublishedMixin behavior that unpublishes records when they're
        # archived.
        bottle.with_context(active_test=False).write({
            'active': True,
            'website_published': True,
        })
        self.start_tour(
            bottle.website_url,
            'website_sale_wishlist.no_valid_combination'
        )
