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

    def test_exclusions_include_ptav_of_line_emptied_by_archived_value(self):
        """
        Test that a ptav whose value was archived, orphaning its attribute line, still gets a
        key in the exclusions dict when it's part of the combination being checked. Otherwise
        the frontend's unguarded exclusions[ptavId] lookup throws and takes the configurator
        down.
        """
        # A value can only be archived (not deleted) while still used by an active variant.
        engraving = self.env['product.attribute'].create({
            'name': 'Engraving',
            'create_variant': 'dynamic',
            'value_ids': [Command.create({'name': 'custom text'})],
        })
        product_template = self.env['product.template'].create({
            'name': 'Shirt',
            'categ_id': self.product_category.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': self.color_attribute.id,
                'value_ids': [Command.set([self.color_attribute_red.id])],
            })],
        })
        variant = product_template.product_variant_ids
        product_template.write({
            'attribute_line_ids': [Command.create({
                'attribute_id': engraving.id,
                'value_ids': [Command.set(engraving.value_ids.ids)],
            })],
        })
        dynamic_line = product_template.attribute_line_ids.filtered(lambda ptal: ptal.attribute_id == engraving)
        dynamic_ptav = dynamic_line.product_template_value_ids

        product_template.action_archive()
        engraving.value_ids.unlink()
        product_template.action_unarchive()

        # The value is gone from the line, but the ptav stays active and usable.
        self.assertFalse(dynamic_line.value_ids)
        self.assertTrue(dynamic_ptav.ptav_active)
        self.assertNotIn(dynamic_line, product_template.valid_product_template_attribute_line_ids)

        self.authenticate('demo', 'demo')
        ptav_ids = variant.product_template_attribute_value_ids.ids + [dynamic_ptav.id]
        result = self.request_get_values(product_template, ptav_ids)
        exclusions = result['products'][0]['exclusions']
        # A combination naming the ptav must get a key for it, or the frontend's unguarded
        # exclusions[ptavId] lookup throws.
        self.assertIn(str(dynamic_ptav.id), exclusions)
        self.assertEqual(exclusions[str(dynamic_ptav.id)], [])

        # Not fabricated when the ptav isn't part of the checked combination.
        result = self.request_get_values(product_template, variant.product_template_attribute_value_ids.ids)
        self.assertNotIn(str(dynamic_ptav.id), result['products'][0]['exclusions'])

    def test_reopening_with_a_line_emptied_by_an_archived_value_does_not_reselect_it(self):
        """
        Test that reopening the configurator on a combination that omits a line whose only value
        was archived doesn't silently reselect that value for it. Before this fix, the "fill in
        missing attributes" backfill only checked ptav_active (untouched by archiving the
        underlying value), so it would resurrect a value a fresh combination could never offer,
        making the line appear as configured (with a lone unusable option) instead of empty, like
        it does for a brand-new line requesting the same template.
        """
        # A value can only be archived (not deleted) while still used by an active variant.
        engraving = self.env['product.attribute'].create({
            'name': 'Engraving',
            'create_variant': 'dynamic',
            'value_ids': [Command.create({'name': 'custom text'})],
        })
        product_template = self.env['product.template'].create({
            'name': 'Shirt',
            'categ_id': self.product_category.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': self.color_attribute.id,
                'value_ids': [Command.set([self.color_attribute_red.id])],
            })],
        })
        color_line = product_template.attribute_line_ids
        product_template.write({
            'attribute_line_ids': [Command.create({
                'attribute_id': engraving.id,
                'value_ids': [Command.set(engraving.value_ids.ids)],
            })],
        })
        dynamic_line = product_template.attribute_line_ids.filtered(lambda ptal: ptal.attribute_id == engraving)
        dynamic_ptav = dynamic_line.product_template_value_ids

        product_template.action_archive()
        engraving.value_ids.unlink()
        product_template.action_unarchive()
        self.assertTrue(dynamic_ptav.ptav_active)

        self.authenticate('demo', 'demo')
        # Reopen on a combination that doesn't mention the dynamic line, same as an order line
        # saved before that line was ever added to the template.
        result = self.request_get_values(product_template, color_line.product_template_value_ids.ids)
        result_line = next(
            line for line in result['products'][0]['attribute_lines'] if line['id'] == dynamic_line.id
        )
        self.assertNotIn(dynamic_ptav.id, result_line['selected_attribute_value_ids'])

    def test_fresh_combination_not_excluded_by_a_variant_archived_via_a_deleted_value(self):
        """
        Test that a combination made only of currently-active values isn't flagged as an
        "archived combination" (and therefore barred) just because deleting one template's
        dynamic value left behind an archived variant that still reports the value's ptav as
        `ptav_active`. Otherwise a brand-new line for that same template inherits a stale
        variant's leftover state for no reason visible to the user. Reopening the line that
        genuinely has the stale value in its own saved combination should still see it flagged,
        same as before this fix.
        """
        engraving = self.env['product.attribute'].create({
            'name': 'Engraving',
            'create_variant': 'dynamic',
            'value_ids': [Command.create({'name': 'custom text', 'is_custom': True})],
        })
        product_template = self.env['product.template'].create({
            'name': 'Shirt',
            'categ_id': self.product_category.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': self.color_attribute.id,
                'value_ids': [Command.set([
                    self.color_attribute_red.id, self.color_attribute_blue.id,
                ])],
            })],
        })
        product_template.write({
            'attribute_line_ids': [Command.create({
                'attribute_id': engraving.id,
                'value_ids': [Command.set(engraving.value_ids.ids)],
            })],
        })
        # Confirm a line while the engraving value is still active, materializing a variant
        # whose own combination includes it - this is the variant that becomes archived below.
        red_variant = product_template.product_variant_ids.filtered(
            lambda p: self.color_attribute_red in p.product_template_attribute_value_ids.product_attribute_value_id
        )
        stale_combination_ids = red_variant.product_template_attribute_value_ids.ids
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': red_variant.id,
                'product_uom_qty': 1,
            })],
        })
        order.action_confirm()

        # Archiving the template lets the in-use engraving value be deleted instead of blocked;
        # the variant that had it in its combination is archived (not deleted) as a result.
        product_template.action_archive()
        engraving.value_ids.unlink()
        product_template.action_unarchive()

        self.authenticate('demo', 'demo')

        # A brand-new line doesn't mention the stale variant's combination at all: it should not
        # see it in archived_combinations, or it would bar an otherwise fully valid Red option.
        new_line_result = self.request_get_values(product_template)
        self.assertNotIn(
            stale_combination_ids,
            [sorted(c) for c in new_line_result['products'][0]['archived_combinations']],
        )

        # Reopening the order line that genuinely has the stale combination should still see it
        # flagged: that variant really was materialized with a value since archived.
        reopen_result = self.request_get_values(product_template, stale_combination_ids)
        self.assertIn(
            stale_combination_ids,
            [sorted(c) for c in reopen_result['products'][0]['archived_combinations']],
        )

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
