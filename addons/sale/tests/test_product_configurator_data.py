# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.product.tests.common import ProductAttributesCommon, ProductVariantsCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestProductConfiguratorData(HttpCaseWithUserDemo, ProductVariantsCommon, SaleCommon):

    def request_get_values(self, product_template, ptav_ids=None):
        base_url = product_template.get_base_url()
        response = self.opener.post(
            url=base_url + '/sale/product_configurator/get_values',
            json={
                'params': {
                    'product_template_id': product_template.id,
                    'quantity': 1.0,
                    'currency_id': 1,
                    'so_date': str(self.env.cr.now()),
                    'product_uom_id': None,
                    'company_id': None,
                    'pricelist_id': None,
                    'ptav_ids': ptav_ids,
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

    def create_product_template_with_attribute_no_variant(self):
        return self.env['product.template'].create({
            'name': 'Chair',
            'categ_id': self.product_category.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.no_variant_attribute.id,
                    'value_ids': [
                        Command.set([
                            self.no_variant_attribute_extra.id
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

    def create_product_template_with_2_attribute_no_variant(self):
        return self.env['product.template'].create({
            'name': 'Chair',
            'categ_id': self.product_category.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.no_variant_attribute.id,
                    'value_ids': [
                        Command.set([
                            self.no_variant_attribute_extra.id,
                            self.no_variant_attribute_second.id,
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

    def test_dropped_attribute_value(self):
        product_template = self.create_product_template_with_2_attributes()
        self.assertEqual(len(product_template.product_variant_ids), 4)

        # Use variants s.t. they are archived and not deleted when value is removed
        self.empty_order.order_line = [
            Command.create(
                {
                    'product_id': product.id
                }
            )
            for product in product_template.product_variant_ids
        ]
        self.empty_order.action_confirm()

        # Remove attribute value red
        product_template.attribute_line_ids.filtered(
            lambda ptal: ptal.attribute_id == self.color_attribute
        ).value_ids = [Command.unlink(self.color_attribute_red.id)]
        self.assertEqual(len(product_template.product_variant_ids), 2)
        archived_variants = product_template.with_context(
            active_test=False
        ).product_variant_ids - product_template.product_variant_ids
        self.assertEqual(len(archived_variants), 2)

        archived_ptav = product_template.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == self.color_attribute_red
        )
        # Choose the variant (red, L)
        variant_ptav_ids = [
            archived_ptav.id,
            product_template.attribute_line_ids.product_template_value_ids.filtered(
                lambda ptav: ptav.product_attribute_value_id == self.size_attribute_l
            ).id,
        ]
        self.authenticate('demo', 'demo')
        result = self.request_get_values(product_template, variant_ptav_ids)
        archived_ptav = archived_variants.product_template_attribute_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == self.color_attribute_red
        )

        # When requested combination contains inactive ptav
        # check that archived combinations are loaded
        self.assertEqual(
            len(result['products'][0]['archived_combinations']),
            2
        )
        for combination in result['products'][0]['archived_combinations']:
            self.assertIn(archived_ptav.id, combination)

        # When requested combination contains inactive ptav check that exclusions contains it
        self.assertIn(str(archived_ptav.id), result['products'][0]['exclusions'])

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

    def test_ptal_values_set_for_no_variant_atribute(self):
        '''
        Test that selected_attribute_value_id is set for attribute with only one variant and
        `create_variant`: `no_variant`.
        '''
        product_template = self.create_product_template_with_attribute_no_variant()

        self.authenticate('demo', 'demo')

        ptav_red = product_template.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == self.color_attribute_red
        )
        result = self.request_get_values(product_template, [ptav_red.id])
        self.assertTrue(result['products'][0]['attribute_lines'][1]['selected_attribute_value_ids'])

    def test_dropped_attribute_value_custom_no_variant(self):
        product_template = self.create_product_template_with_2_attribute_no_variant()

        # Use variants s.t. they are archived and not deleted when value is removed

        self.empty_order.order_line = [
            Command.create({
                'product_id': product.id,
                'product_no_variant_attribute_value_ids': product.attribute_line_ids.product_template_value_ids.filtered(
                    lambda p: p.attribute_id.create_variant == 'no_variant'
                ),
            })
            for product in product_template.product_variant_ids]
        self.empty_order.action_confirm()

        # Remove attribute value extra
        product_template.attribute_line_ids.filtered(
            lambda ptal: ptal.attribute_id == self.no_variant_attribute
        ).value_ids = [Command.unlink(self.no_variant_attribute_extra.id)]

        archived_ptav = product_template.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == self.no_variant_attribute_extra
        )
        self.assertFalse(archived_ptav.ptav_active)
        self.assertEqual(
            product_template.attribute_line_ids.filtered(
                lambda ptal: ptal.attribute_id == self.no_variant_attribute
            ).product_template_value_ids[0],
            archived_ptav,
        )
        # Choose the variant (red)
        variant_ptav_ids = [
            product_template.attribute_line_ids.product_template_value_ids.filtered(
                lambda ptav: ptav.product_attribute_value_id == self.color_attribute_red
            ).id,
        ]
        self.authenticate('demo', 'demo')
        result = self.request_get_values(product_template, variant_ptav_ids)
        selected_values = [
            selected_value
            for product in result['products'][0]['attribute_lines']
            for selected_value in product['selected_attribute_value_ids']]

        # Make sure that deleted value is not selected
        self.assertNotIn(archived_ptav.id, selected_values)

    def test_multiple_attribute_lines_same_attribute(self):
        """
        Test that product configurator works correctly when multiple attribute
        lines reference the same attribute. This ensures no KeyError is raised
        when building the attrs_map in _get_product_information.
        """
        # Create a product template with two attribute lines referencing the same attribute
        product_template = self.env['product.template'].create({
            'name': 'Multi Size Shirt',
            'categ_id': self.product_category.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [
                        Command.set([
                            self.size_attribute_l.id,
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
                Command.create({
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [
                        Command.set([
                            self.size_attribute_m.id,
                        ]),
                    ],
                }),
            ],
        })

        self.authenticate('demo', 'demo')
        # This should not raise a KeyError
        result = self.request_get_values(product_template)

        # Verify we got the expected number of attribute lines
        self.assertEqual(len(result['products'][0]['attribute_lines']), 3)
        # Verify that each attribute line has its attribute info correctly mapped
        attribute_names = [
            line['attribute']['name']
            for line in result['products'][0]['attribute_lines']
        ]
        self.assertIn('Size', attribute_names)
        self.assertIn('Color', attribute_names)
        # Count occurrences of 'Size' - should be 2 since we have two lines with the same attribute
        self.assertEqual(attribute_names.count('Size'), 2)


@tagged('post_install', '-at_install')
class TestSaleProductVariants(ProductAttributesCommon, SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_template_2lines_2attributes = cls.env['product.template'].create({
            'name': '2 lines 2 attributes',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'categ_id': cls.product_category.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': cls.color_attribute.id,
                    'value_ids': [Command.set([
                        cls.color_attribute_red.id,
                        cls.color_attribute_blue.id,
                    ])],
                }),
                Command.create({
                    'attribute_id': cls.size_attribute.id,
                    'value_ids': [Command.set([
                        cls.size_attribute_s.id,
                        cls.size_attribute_m.id,
                    ])]
                })
            ]
        })

        # Sell all variants
        cls.empty_order.order_line = [
            Command.create({
                'product_id': product.id,
            })
            for product in cls.product_template_2lines_2attributes.product_variant_ids
        ]

    def test_attribute_removal(self):
        def _get_ptavs():
            return self.product_template_2lines_2attributes.with_context(
                active_test=False
            ).attribute_line_ids.product_template_value_ids

        def _get_archived_variants():
            return self.product_template_2lines_2attributes.with_context(
                active_test=False
            ).product_variant_ids.filtered(lambda p: not p.active)

        def _get_active_variants():
            return self.product_template_2lines_2attributes.product_variant_ids

        self.assertEqual(len(_get_ptavs()), 4)
        self.product_template_2lines_2attributes.attribute_line_ids = [
            Command.unlink(self.product_template_2lines_2attributes.attribute_line_ids.filtered(
                lambda ptal: ptal.attribute_id.id == self.size_attribute.id
            ).id)
        ]
        self.assertEqual(len(_get_ptavs()), 4)

        # Use products s.t. they are archived and not deleted
        self.empty_order.order_line = [
            Command.create({
                'product_id': product.id,
            })
            for product in self.product_template_2lines_2attributes.product_variant_ids
        ]

        self.assertEqual(len(_get_archived_variants()), 4)
        self.assertEqual(len(_get_active_variants()), 2)

        self.product_template_2lines_2attributes.attribute_line_ids = [
            Command.create({
                'attribute_id': self.size_attribute.id,
                'value_ids': [Command.set([
                    self.size_attribute_s.id,
                ])]
            })
        ]
        self.assertEqual(len(_get_ptavs()), 4)
        self.assertEqual(len(_get_active_variants()), 2)
        self.assertEqual(len(_get_archived_variants()), 4)

        # When adding a single attribute line, the attribute will be added to all existing variants
        # Instead of unarchiving existing archived variants with the same combination
        # Leading to a state where the database holds two variants with the same combination
        # We don't want this combination to be excluded from the product configurator as it is valid
        # as long as there is one active variant with this configuration.
        exclusions_data = self.product_template_2lines_2attributes._get_attribute_exclusions()
        self.assertTrue(
            all(
                tuple(product.product_template_attribute_value_ids.ids) not in exclusions_data['archived_combinations']
                for product in _get_active_variants()
            )
        )
