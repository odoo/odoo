# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestProductConfiguratorData(HttpCase, ProductVariantsCommon, SaleCommon):

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
        base_url = self.product_template_sofa.get_base_url()
        response = self.opener.post(
            url=base_url + '/sale_product_configurator/get_values',
            json={
                'params': dict(
                    product_template_id=self.product_template_sofa.id,
                    quantity=1.0,
                    currency_id=1,
                    so_date=str(self.env.cr.now()),
                    product_uom_id=None,
                    company_id=None,
                    pricelist_id=None,
                    ptav_ids=None,
                    only_main_product=False,
                ),
            }
        )
        result = response.json()['result']

        # Make sure the inactive ptav was removed from the loaded attributes
        self.assertEqual(len(result['products'][0]['attribute_lines'][0]['attribute_values']), 2)

    def test_dropped_attribute(self):
        self.product_template_2_attribute_lines = self.env['product.template'].create({
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
        self.assertEqual(len(self.product_template_2_attribute_lines.product_variant_ids), 4)

        # Use variants s.t. they are archived and not deleted when value is removed
        self.empty_order.order_line = [
            Command.create({
                'product_id': product.id
            })
            for product in self.product_template_2_attribute_lines.product_variant_ids
        ]
        self.empty_order.action_confirm()

        # Remove attribute
        self.product_template_2_attribute_lines.attribute_line_ids[0].unlink()
        self.assertEqual(len(self.product_template_2_attribute_lines.product_variant_ids), 2)

        self.authenticate('demo', 'demo')
        base_url = self.product_template_2_attribute_lines.get_base_url()
        response = self.opener.post(
            url=base_url + '/sale_product_configurator/get_values',
            json={
                'params': {
                    'product_template_id': self.product_template_2_attribute_lines.id,
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
        result = response.json()['result']

        # Make sure archived combinations with inactive ptav are not loaded as it's useless to
        # exclude combinations that are not even available
        self.assertFalse(result['products'][0]['archived_combinations'])
