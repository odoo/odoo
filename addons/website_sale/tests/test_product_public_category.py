# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestProductPublicCategory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def create_multi(vals_list):
            return list(map(Command.create, vals_list))

        cls.published_product, cls.unpublished_product = cls.env['product.template'].create([
            {'name': 'Published Product', 'is_published': True},
            {'name': 'Unpublished Product', 'is_published': False},
        ])

        cls.env['product.public.category'].search([]).unlink()

        cls.env['product.public.category'].create([
            {
                'name': '1',
                'child_id': create_multi([
                    {
                        'name': '1.1',
                        'child_id': create_multi([{'name': '1.1.1'}]),
                    },
                    {'name': '1.2', 'product_tmpl_ids': [Command.link(cls.published_product.id)]},
                ]),
            },
            {
                'name': '2',
                'child_id': create_multi([
                    {
                        'name': '2.1',
                        'child_id': create_multi([{
                            'name': '2.1.1',
                            'product_tmpl_ids': [
                                Command.link(cls.published_product.id),
                                Command.link(cls.unpublished_product.id)
                            ],
                        }]),
                    },
                    {'name': '2.2'},
                ]),
            },
            {'name': '3', 'product_tmpl_ids': [Command.link(cls.unpublished_product.id)]},
        ])

    def test_search_has_published_products(self):
        published_categs = set(self.env['product.public.category'].search(
            [('has_published_products', 'not in', (False,))]
        ).mapped('name'))

        self.assertSetEqual(published_categs, {'1', '1.2', '2', '2.1', '2.1.1'})

    def test_search_does_not_have_published_products(self):
        unpublished_categs = set(self.env['product.public.category'].search(
            [('has_published_products', '!=', True)]
        ).mapped('name'))

        self.assertSetEqual(unpublished_categs, {'1.1', '1.1.1', '2.2', '3'})
