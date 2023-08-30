# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestProductConfiguratorData(HttpCase, ProductVariantsCommon, SaleCommon):

    def request_get_values(self, product_template):
        base_url = product_template.get_base_url()
        response = self.opener.post(
            url=base_url + '/sale_product_configurator/get_values',
            json={
                'params': {
                    'product_template_id': product_template.id,
                    'quantity': 1.0,
                    'currency_id': 1,
                    'so_date': str(self.env.cr.now()),
                    'product_uom_id': None,
                    'company_id': None,
                    'pricelist_id': None,
                    'ptav_ids': None,
                    'only_main_product': False,
                },
            }
        )
        return response.json()['result']

    def create_product_template_with_2_attributes(self):
        return self.env['product.template'].create({
            'name': 'Shirt',
            'categ_id': self.product_category.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [
                        Command.set([
                            self.size_attribute_l.id,
                            self.size_attribute_m.id,
                        ]),
                    ],
                }),
                Command.create({
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [
                        Command.set([
                            self.color_attribute_red.id,
                            self.color_attribute_blue.id,
                        ])
                    ],
                }),
            ],
        })

    def test_dropped_value_isnt_shown(self):
        self.assertEqual(len(self.product_template_sofa.product_variant_ids), 3)

        # Use variants s.t. they are archived and not deleted when value is removed
        self.empty_order.order_line = [
            Command.create({
                'product_id': product.id
            })
            for product in self.product_template_sofa.product_variant_ids
        ]
        self.empty_order.action_confirm()

        # Remove attribute value
        self.product_template_sofa.attribute_line_ids.value_ids -= self.color_attribute_red
        self.assertEqual(len(self.product_template_sofa.product_variant_ids.filtered('active')), 2)

        self.authenticate('demo', 'demo')
        result = self.request_get_values(self.product_template_sofa)

        # Make sure the inactive ptav was removed from the loaded attributes
        self.assertEqual(len(result['products'][0]['attribute_lines'][0]['attribute_values']), 2)

    def test_dropped_attribute(self):
        product_template = self.create_product_template_with_2_attributes()
        self.assertEqual(len(product_template.product_variant_ids), 4)

        # Use variants s.t. they are archived and not deleted when value is removed
        self.empty_order.order_line = [
            Command.create({
                'product_id': product.id
            })
            for product in product_template.product_variant_ids
        ]
        self.empty_order.action_confirm()

        # Remove attribute
        product_template.attribute_line_ids[0].unlink()
        self.assertEqual(len(product_template.product_variant_ids), 2)

        self.authenticate('demo', 'demo')
        result = self.request_get_values(product_template)

        # Make sure archived combinations with inactive ptav are not loaded as it's useless to
        # exclude combinations that are not even available
        self.assertFalse(result['products'][0]['archived_combinations'])

    def test_excluded_inactive_ptav(self):
        product_template = self.create_product_template_with_2_attributes()
        self.assertEqual(len(product_template.product_variant_ids), 4)

        ptav_with_exclusion = product_template.attribute_line_ids[0].product_template_value_ids[0]
        ptav_excluded = product_template.attribute_line_ids[1].product_template_value_ids[0]

        # Add an exclusion
        ptav_with_exclusion.write({
            'exclude_for': [
                Command.create({
                    'product_tmpl_id': product_template.id,
                    'value_ids': [
                        Command.set([
                            ptav_excluded.id,
                        ]),
                    ],
                }),
            ],
        })
        self.assertEqual(len(product_template.product_variant_ids), 3)

        self.authenticate('demo', 'demo')
        result = self.request_get_values(product_template)
        # The PTAVs should be mutually excluded
        self.assertEqual(result['products'][0]['exclusions']
                         [str(ptav_with_exclusion.id)], [ptav_excluded.id])
        self.assertEqual(result['products'][0]['exclusions']
                         [str(ptav_excluded.id)], [ptav_with_exclusion.id])

        ptav_with_exclusion.write({'ptav_active': False})
        result = self.request_get_values(product_template)
        # The inactive PTAV should not be in the product exclusions dict
        self.assertFalse(str(ptav_with_exclusion.id) in result['products'][0]['exclusions'])
        # The inactive PTAV should not be in the exclusions of the excluded PTAV
        self.assertEqual(result['products'][0]['exclusions'][str(ptav_excluded.id)], [])

        ptav_with_exclusion.write({'ptav_active': True})
        ptav_excluded.write({'ptav_active': False})
        result = self.request_get_values(product_template)
        # The excluded inactive PTAV should not be in the exclusions of the first PTAV
        self.assertEqual(result['products'][0]['exclusions'][str(ptav_with_exclusion.id)], [])
        # The excluded inactive PTAV should not be in the product exclusions dict
        self.assertFalse(str(ptav_excluded.id) in result['products'][0]['exclusions'])

        ptav_with_exclusion.write({'ptav_active': False})
        ptav_excluded.write({'ptav_active': False})
        result = self.request_get_values(product_template)

        # The inactive PTAVs should not be in the product exclusions dict
        self.assertFalse(str(ptav_with_exclusion.id) in result['products'][0]['exclusions'])
        self.assertFalse(str(ptav_excluded.id) in result['products'][0]['exclusions'])
