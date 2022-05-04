# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestProductAttributeValueCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestProductAttributeValueCommon, cls).setUpClass()

        cls.computer = cls.env['product.template'].create({
            'name': 'Super Computer',
            'price': 2000,
        })

        cls._add_ssd_attribute()
        cls._add_ram_attribute()
        cls._add_hdd_attribute()

        cls.computer_case = cls.env['product.template'].create({
            'name': 'Super Computer Case'
        })

        cls._add_size_attribute()

    @classmethod
    def _add_ssd_attribute(cls):
        cls.ssd_attribute = cls.env['product.attribute'].create({'name': 'Memory', 'sequence': 1})
        cls.ssd_256 = cls.env['product.attribute.value'].create({
            'name': '256 GB',
            'attribute_id': cls.ssd_attribute.id,
            'sequence': 1,
        })
        cls.ssd_512 = cls.env['product.attribute.value'].create({
            'name': '512 GB',
            'attribute_id': cls.ssd_attribute.id,
            'sequence': 2,
        })

        cls._add_ssd_attribute_line()

    @classmethod
    def _add_ssd_attribute_line(cls):
        cls.computer_ssd_attribute_lines = cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.computer.id,
            'attribute_id': cls.ssd_attribute.id,
            'value_ids': [(6, 0, [cls.ssd_256.id, cls.ssd_512.id])],
        })
        cls.computer_ssd_attribute_lines.product_template_value_ids[0].price_extra = 200
        cls.computer_ssd_attribute_lines.product_template_value_ids[1].price_extra = 400

    @classmethod
    def _add_ram_attribute(cls):
        cls.ram_attribute = cls.env['product.attribute'].create({'name': 'RAM', 'sequence': 2})
        cls.ram_8 = cls.env['product.attribute.value'].create({
            'name': '8 GB',
            'attribute_id': cls.ram_attribute.id,
            'sequence': 1,
        })
        cls.ram_16 = cls.env['product.attribute.value'].create({
            'name': '16 GB',
            'attribute_id': cls.ram_attribute.id,
            'sequence': 2,
        })
        cls.ram_32 = cls.env['product.attribute.value'].create({
            'name': '32 GB',
            'attribute_id': cls.ram_attribute.id,
            'sequence': 3,
        })
        cls.computer_ram_attribute_lines = cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.computer.id,
            'attribute_id': cls.ram_attribute.id,
            'value_ids': [(6, 0, [cls.ram_8.id, cls.ram_16.id, cls.ram_32.id])],
        })
        cls.computer_ram_attribute_lines.product_template_value_ids[0].price_extra = 20
        cls.computer_ram_attribute_lines.product_template_value_ids[1].price_extra = 40
        cls.computer_ram_attribute_lines.product_template_value_ids[2].price_extra = 80

    @classmethod
    def _add_hdd_attribute(cls):
        cls.hdd_attribute = cls.env['product.attribute'].create({'name': 'HDD', 'sequence': 3})
        cls.hdd_1 = cls.env['product.attribute.value'].create({
            'name': '1 To',
            'attribute_id': cls.hdd_attribute.id,
            'sequence': 1,
        })
        cls.hdd_2 = cls.env['product.attribute.value'].create({
            'name': '2 To',
            'attribute_id': cls.hdd_attribute.id,
            'sequence': 2,
        })
        cls.hdd_4 = cls.env['product.attribute.value'].create({
            'name': '4 To',
            'attribute_id': cls.hdd_attribute.id,
            'sequence': 3,
        })

        cls._add_hdd_attribute_line()

    @classmethod
    def _add_hdd_attribute_line(cls):
        cls.computer_hdd_attribute_lines = cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.computer.id,
            'attribute_id': cls.hdd_attribute.id,
            'value_ids': [(6, 0, [cls.hdd_1.id, cls.hdd_2.id, cls.hdd_4.id])],
        })
        cls.computer_hdd_attribute_lines.product_template_value_ids[0].price_extra = 2
        cls.computer_hdd_attribute_lines.product_template_value_ids[1].price_extra = 4
        cls.computer_hdd_attribute_lines.product_template_value_ids[2].price_extra = 8

    def _add_ram_exclude_for(self):
        self._get_product_value_id(self.computer_ram_attribute_lines, self.ram_16).update({
            'exclude_for': [(0, 0, {
                'product_tmpl_id': self.computer.id,
                'value_ids': [(6, 0, [self._get_product_value_id(self.computer_hdd_attribute_lines, self.hdd_1).id])]
            })]
        })

    @classmethod
    def _add_size_attribute(cls):
        cls.size_attribute = cls.env['product.attribute'].create({'name': 'Size', 'sequence': 4})
        cls.size_m = cls.env['product.attribute.value'].create({
            'name': 'M',
            'attribute_id': cls.size_attribute.id,
            'sequence': 1,
        })
        cls.size_l = cls.env['product.attribute.value'].create({
            'name': 'L',
            'attribute_id': cls.size_attribute.id,
            'sequence': 2,
        })
        cls.size_xl = cls.env['product.attribute.value'].create({
            'name': 'XL',
            'attribute_id': cls.size_attribute.id,
            'sequence': 3,
        })
        cls.computer_case_size_attribute_lines = cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.computer_case.id,
            'attribute_id': cls.size_attribute.id,
            'value_ids': [(6, 0, [cls.size_m.id, cls.size_l.id, cls.size_xl.id])],
        })

    def _get_product_value_id(self, product_template_attribute_lines, product_attribute_value):
        return product_template_attribute_lines.product_template_value_ids.filtered(
            lambda product_value_id: product_value_id.product_attribute_value_id == product_attribute_value)[0]

    def _get_product_template_attribute_value(self, product_attribute_value, model=False):
        """
            Return the `product.template.attribute.value` matching
                `product_attribute_value` for self.

            :param: recordset of one product.attribute.value
            :return: recordset of one product.template.attribute.value if found
                else empty
        """
        if not model:
            model = self.computer
        return model.valid_product_template_attribute_line_ids.filtered(
            lambda l: l.attribute_id == product_attribute_value.attribute_id
        ).product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == product_attribute_value
        )

    def _add_exclude(self, m1, m2, product_template=False):
        m1.update({
            'exclude_for': [(0, 0, {
                'product_tmpl_id': (product_template or self.computer).id,
                'value_ids': [(6, 0, [m2.id])]
            })]
        })


@tagged('post_install', '-at_install')
class TestProductAttributeValueConfig(TestProductAttributeValueCommon):

    def test_product_template_attribute_values_creation(self):
        self.assertEqual(len(self.computer_ssd_attribute_lines.product_template_value_ids), 2,
            'Product attribute values (ssd) were not automatically created')
        self.assertEqual(len(self.computer_ram_attribute_lines.product_template_value_ids), 3,
            'Product attribute values (ram) were not automatically created')
        self.assertEqual(len(self.computer_hdd_attribute_lines.product_template_value_ids), 3,
            'Product attribute values (hdd) were not automatically created')
        self.assertEqual(len(self.computer_case_size_attribute_lines.product_template_value_ids), 3,
            'Product attribute values (size) were not automatically created')

    def test_get_variant_for_combination(self):
        computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
        computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
        computer_ram_16 = self._get_product_template_attribute_value(self.ram_16)
        computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)

        # completely defined variant
        combination = computer_ssd_256 + computer_ram_8 + computer_hdd_1
        ok_variant = self.computer._get_variant_for_combination(combination)
        self.assertEqual(ok_variant.product_template_attribute_value_ids, combination)

        # over defined variant
        combination = computer_ssd_256 + computer_ram_8 + computer_ram_16 + computer_hdd_1
        variant = self.computer._get_variant_for_combination(combination)
        self.assertEqual(len(variant), 0)

        # under defined variant
        combination = computer_ssd_256 + computer_ram_8
        variant = self.computer._get_variant_for_combination(combination)
        self.assertFalse(variant)

    def test_product_filtered_exclude_for(self):
        """
            Super Computer has 18 variants total (2 ssd * 3 ram * 3 hdd)
            RAM 16 excludes HDD 1, that matches 2 variants:
            - SSD 256 RAM 16 HDD 1
            - SSD 512 RAM 16 HDD 1

            => There has to be 16 variants left when filtered
        """
        computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
        computer_ssd_512 = self._get_product_template_attribute_value(self.ssd_512)
        computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
        computer_ram_16 = self._get_product_template_attribute_value(self.ram_16)
        computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)

        self.assertEqual(len(self.computer._get_possible_variants()), 18)
        self._add_ram_exclude_for()
        self.assertEqual(len(self.computer._get_possible_variants()), 16)
        self.assertTrue(self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_1)._is_variant_possible())
        self.assertFalse(self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_16 + computer_hdd_1))
        self.assertFalse(self.computer._get_variant_for_combination(computer_ssd_512 + computer_ram_16 + computer_hdd_1))

    def test_children_product_filtered_exclude_for(self):
        """
            Super Computer Case has 3 variants total (3 size)
            Reference product Computer with HDD 4 excludes Size M
            The following variant will be excluded:
            - Size M

            => There has to be 2 variants left when filtered
        """
        computer_hdd_4 = self._get_product_template_attribute_value(self.hdd_4)
        computer_size_m = self._get_product_template_attribute_value(self.size_m, self.computer_case)
        self._add_exclude(computer_hdd_4, computer_size_m, self.computer_case)
        self.assertEqual(len(self.computer_case._get_possible_variants(computer_hdd_4)), 2)
        self.assertFalse(self.computer_case._get_variant_for_combination(computer_size_m)._is_variant_possible(computer_hdd_4))

    def test_is_combination_possible(self):
        computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
        computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
        computer_ram_16 = self._get_product_template_attribute_value(self.ram_16)
        computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
        self._add_exclude(computer_ram_16, computer_hdd_1)

        # CASE: basic
        self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

        # CASE: ram 16 excluding hdd1
        self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_16 + computer_hdd_1))

        # CASE: under defined combination
        self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_16))

        # CASE: no combination, no variant, just return the only variant
        mouse = self.env['product.template'].create({'name': 'Mouse'})
        self.assertTrue(mouse._is_combination_possible(self.env['product.template.attribute.value']))

        # prep work for the last part of the test
        color_attribute = self.env['product.attribute'].create({'name': 'Color'})
        color_red = self.env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': color_attribute.id,
        })
        color_green = self.env['product.attribute.value'].create({
            'name': 'Green',
            'attribute_id': color_attribute.id,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': mouse.id,
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, [color_red.id, color_green.id])],
        })

        mouse_color_red = self._get_product_template_attribute_value(color_red, mouse)
        mouse_color_green = self._get_product_template_attribute_value(color_green, mouse)

        self._add_exclude(computer_ssd_256, mouse_color_green, mouse)

        variant = self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_1)

        # CASE: wrong attributes (mouse_color_red not on computer)
        self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_16 + mouse_color_red))

        # CASE: parent ok
        self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1, mouse_color_red))
        self.assertTrue(mouse._is_combination_possible(mouse_color_red, computer_ssd_256 + computer_ram_8 + computer_hdd_1))

        # CASE: parent exclusion but good direction (parent is directional)
        self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1, mouse_color_green))

        # CASE: parent exclusion and wrong direction (parent is directional)
        self.assertFalse(mouse._is_combination_possible(mouse_color_green, computer_ssd_256 + computer_ram_8 + computer_hdd_1))

        # CASE: deleted combination
        variant.unlink()
        self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

        # CASE: if multiple variants exist for the same combination and at least
        # one of them is not archived, the combination is possible
        combination = computer_ssd_256 + computer_ram_8 + computer_hdd_1
        self.env['product.product'].create({
            'product_tmpl_id': self.computer.id,
            'product_template_attribute_value_ids': [(6, 0, combination.ids)],
            'active': False,
        })
        self.env['product.product'].create({
            'product_tmpl_id': self.computer.id,
            'product_template_attribute_value_ids': [(6, 0, combination.ids)],
            'active': True,
        })
        self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

    def test_get_first_possible_combination(self):
        computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
        computer_ssd_512 = self._get_product_template_attribute_value(self.ssd_512)
        computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
        computer_ram_16 = self._get_product_template_attribute_value(self.ram_16)
        computer_ram_32 = self._get_product_template_attribute_value(self.ram_32)
        computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
        computer_hdd_2 = self._get_product_template_attribute_value(self.hdd_2)
        computer_hdd_4 = self._get_product_template_attribute_value(self.hdd_4)
        self._add_exclude(computer_ram_16, computer_hdd_1)

        # Basic case: test all iterations of generator
        gen = self.computer._get_possible_combinations()
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_8 + computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_8 + computer_hdd_2)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_8 + computer_hdd_4)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_16 + computer_hdd_2)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_16 + computer_hdd_4)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_32 + computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_32 + computer_hdd_2)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_32 + computer_hdd_4)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_8 + computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_8 + computer_hdd_2)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_8 + computer_hdd_4)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_16 + computer_hdd_2)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_16 + computer_hdd_4)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_32 + computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_32 + computer_hdd_2)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_32 + computer_hdd_4)
        self.assertIsNone(next(gen, None))

        # Give priority to ram_16 but it is not allowed by hdd_1 so it should return hhd_2 instead
        # Test invalidate_cache on product.attribute.value write
        computer_ram_16.product_attribute_value_id.sequence = -1
        self.assertEqual(self.computer._get_first_possible_combination(), computer_ssd_256 + computer_ram_16 + computer_hdd_2)

        # Move down the ram, so it will try to change the ram instead of the hdd
        # Test invalidate_cache on product.attribute write
        self.ram_attribute.sequence = 10
        self.assertEqual(self.computer._get_first_possible_combination(), computer_ssd_256 + computer_ram_8 + computer_hdd_1)

        # Give priority to ram_32 and is allowed with the rest so it should return it
        self.ram_attribute.sequence = 2
        computer_ram_16.product_attribute_value_id.sequence = 2
        computer_ram_32.product_attribute_value_id.sequence = -1
        self.assertEqual(self.computer._get_first_possible_combination(), computer_ssd_256 + computer_ram_32 + computer_hdd_1)

        # Give priority to ram_16 but now it is not allowing any hdd so it should return ram_8 instead
        computer_ram_32.product_attribute_value_id.sequence = 3
        computer_ram_16.product_attribute_value_id.sequence = -1
        self._add_exclude(computer_ram_16, computer_hdd_2)
        self._add_exclude(computer_ram_16, computer_hdd_4)
        self.assertEqual(self.computer._get_first_possible_combination(), computer_ssd_256 + computer_ram_8 + computer_hdd_1)

        # Only the last combination is possible
        computer_ram_16.product_attribute_value_id.sequence = 2
        self._add_exclude(computer_ram_8, computer_hdd_1)
        self._add_exclude(computer_ram_8, computer_hdd_2)
        self._add_exclude(computer_ram_8, computer_hdd_4)
        self._add_exclude(computer_ram_32, computer_hdd_1)
        self._add_exclude(computer_ram_32, computer_hdd_2)
        self._add_exclude(computer_ram_32, computer_ssd_256)
        self.assertEqual(self.computer._get_first_possible_combination(), computer_ssd_512 + computer_ram_32 + computer_hdd_4)

        # Not possible to add an exclusion when only one variant is left -> it deletes the product template associated to it
        with self.assertRaises(UserError), self.cr.savepoint():
            self._add_exclude(computer_ram_32, computer_hdd_4)

        # If an exclusion rule deletes all variants at once it does not delete the template.
        # Here we can test `_get_first_possible_combination` with a product template with no variants
        # Deletes all exclusions
        for exclusion in computer_ram_32.exclude_for:
            computer_ram_32.write({
                'exclude_for': [(2, exclusion.id, 0)]
            })

        # Activates all exclusions at once
        computer_ram_32.write({
            'exclude_for': [(0, computer_ram_32.exclude_for.id, {
                'product_tmpl_id': self.computer.id,
                'value_ids': [(6, 0, [computer_hdd_1.id, computer_hdd_2.id, computer_hdd_4.id, computer_ssd_256.id, computer_ssd_512.id])]
            })]
        })

        self.assertEqual(self.computer._get_first_possible_combination(), self.env['product.template.attribute.value'])
        gen = self.computer._get_possible_combinations()
        self.assertIsNone(next(gen, None))

        # Testing parent case
        mouse = self.env['product.template'].create({'name': 'Mouse'})
        self.assertTrue(mouse._is_combination_possible(self.env['product.template.attribute.value']))

        # prep work for the last part of the test
        color_attribute = self.env['product.attribute'].create({'name': 'Color'})
        color_red = self.env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': color_attribute.id,
        })
        color_green = self.env['product.attribute.value'].create({
            'name': 'Green',
            'attribute_id': color_attribute.id,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': mouse.id,
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, [color_red.id, color_green.id])],
        })

        mouse_color_red = self._get_product_template_attribute_value(color_red, mouse)
        mouse_color_green = self._get_product_template_attribute_value(color_green, mouse)

        self._add_exclude(computer_ssd_256, mouse_color_red, mouse)
        self.assertEqual(mouse._get_first_possible_combination(parent_combination=computer_ssd_256 + computer_ram_8 + computer_hdd_1), mouse_color_green)

        # Test to see if several attribute_line for same attribute is well handled
        color_blue = self.env['product.attribute.value'].create({
            'name': 'Blue',
            'attribute_id': color_attribute.id,
        })
        color_yellow = self.env['product.attribute.value'].create({
            'name': 'Yellow',
            'attribute_id': color_attribute.id,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': mouse.id,
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, [color_blue.id, color_yellow.id])],
        })
        mouse_color_yellow = self._get_product_template_attribute_value(color_yellow, mouse)
        self.assertEqual(mouse._get_first_possible_combination(necessary_values=mouse_color_yellow), mouse_color_red + mouse_color_yellow)

        # Making sure it's not extremely slow (has to discard invalid combinations early !)
        product_template = self.env['product.template'].create({
            'name': 'many combinations',
        })

        for i in range(10):
            # create the attributes
            product_attribute = self.env['product.attribute'].create({
                'name': "att %s" % i,
                'create_variant': 'dynamic',
                'sequence': i,
            })

            for j in range(50):
                # create the attribute values
                value = self.env['product.attribute.value'].create([{
                    'name': "val %s" % j,
                    'attribute_id': product_attribute.id,
                    'sequence': j,
                }])

            # set attribute and attribute values on the template
            self.env['product.template.attribute.line'].create([{
                'attribute_id': product_attribute.id,
                'product_tmpl_id': product_template.id,
                'value_ids': [(6, 0, product_attribute.value_ids.ids)]
            }])

        self._add_exclude(
            self._get_product_template_attribute_value(product_template.attribute_line_ids[1].value_ids[0],
                                                       model=product_template),
            self._get_product_template_attribute_value(product_template.attribute_line_ids[0].value_ids[0],
                                                       model=product_template),
            product_template)
        self._add_exclude(
            self._get_product_template_attribute_value(product_template.attribute_line_ids[0].value_ids[0],
                                                       model=product_template),
            self._get_product_template_attribute_value(product_template.attribute_line_ids[1].value_ids[1],
                                                       model=product_template),
            product_template)

        combination = self.env['product.template.attribute.value']
        for idx, ptal in enumerate(product_template.attribute_line_ids):
            if idx != 1:
                value = ptal.product_template_value_ids[0]
            else:
                value = ptal.product_template_value_ids[2]
            combination += value

        started_at = time.time()
        self.assertEqual(product_template._get_first_possible_combination(), combination)
        elapsed = time.time() - started_at
        # It should be about instantaneous, 0.5 to avoid false positives
        self.assertLess(elapsed, 0.5)




    def test_get_closest_possible_combinations(self):
        computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
        computer_ssd_512 = self._get_product_template_attribute_value(self.ssd_512)
        computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
        computer_ram_16 = self._get_product_template_attribute_value(self.ram_16)
        computer_ram_32 = self._get_product_template_attribute_value(self.ram_32)
        computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
        computer_hdd_2 = self._get_product_template_attribute_value(self.hdd_2)
        computer_hdd_4 = self._get_product_template_attribute_value(self.hdd_4)
        self._add_exclude(computer_ram_16, computer_hdd_1)

        # CASE nothing special (test 2 iterations)
        gen = self.computer._get_closest_possible_combinations(None)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_8 + computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_8 + computer_hdd_2)

        # CASE contains computer_hdd_1 (test all iterations)
        gen = self.computer._get_closest_possible_combinations(computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_8 + computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_256 + computer_ram_32 + computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_8 + computer_hdd_1)
        self.assertEqual(next(gen), computer_ssd_512 + computer_ram_32 + computer_hdd_1)
        self.assertIsNone(next(gen, None))

        # CASE contains computer_hdd_2
        self.assertEqual(self.computer._get_closest_possible_combination(computer_hdd_2),
            computer_ssd_256 + computer_ram_8 + computer_hdd_2)

        # CASE contains computer_hdd_2, computer_ram_16
        self.assertEqual(self.computer._get_closest_possible_combination(computer_hdd_2 + computer_ram_16),
            computer_ssd_256 + computer_ram_16 + computer_hdd_2)

        # CASE invalid combination (excluded):
        self.assertEqual(self.computer._get_closest_possible_combination(computer_hdd_1 + computer_ram_16),
            computer_ssd_256 + computer_ram_8 + computer_hdd_1)

        # CASE invalid combination (too much):
        self.assertEqual(self.computer._get_closest_possible_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_4 + computer_hdd_2),
            computer_ssd_256 + computer_ram_8 + computer_hdd_4)

        # Make sure this is not extremely slow:
        product_template = self.env['product.template'].create({
            'name': 'many combinations',
        })

        for i in range(10):
            # create the attributes
            product_attribute = self.env['product.attribute'].create({
                'name': "att %s" % i,
                'create_variant': 'dynamic',
                'sequence': i,
            })

            for j in range(10):
                # create the attribute values
                self.env['product.attribute.value'].create([{
                    'name': "val %s/%s" % (i, j),
                    'attribute_id': product_attribute.id,
                    'sequence': j,
                }])

            # set attribute and attribute values on the template
            self.env['product.template.attribute.line'].create([{
                'attribute_id': product_attribute.id,
                'product_tmpl_id': product_template.id,
                'value_ids': [(6, 0, product_attribute.value_ids.ids)]
            }])

        # Get a value in the middle for each attribute to make sure it would
        # take time to reach it (if looping one by one like before the fix).
        combination = self.env['product.template.attribute.value']
        for ptal in product_template.attribute_line_ids:
            combination += ptal.product_template_value_ids[5]

        started_at = time.time()
        self.assertEqual(product_template._get_closest_possible_combination(combination), combination)
        elapsed = time.time() - started_at
        # It should take around 10ms, but to avoid false positives we check an
        # higher value. Before the fix it would take hours.
        self.assertLess(elapsed, 0.5)

    def test_clear_caches(self):
        """The goal of this test is to make sure the cache is invalidated when
        it should be."""
        computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
        computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
        computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
        combination = computer_ssd_256 + computer_ram_8 + computer_hdd_1

        # CASE: initial result of _get_variant_for_combination
        variant = self.computer._get_variant_for_combination(combination)
        self.assertTrue(variant)

        # CASE: clear_caches in product.product unlink
        variant.unlink()
        self.assertFalse(self.computer._get_variant_for_combination(combination))

        # CASE: clear_caches in product.product create
        variant = self.env['product.product'].create({
            'product_tmpl_id': self.computer.id,
            'product_template_attribute_value_ids': [(6, 0, combination.ids)],
        })
        self.assertEqual(variant, self.computer._get_variant_for_combination(combination))

        # CASE: clear_caches in product.product write
        variant.product_template_attribute_value_ids = False
        self.assertFalse(self.computer._get_variant_id_for_combination(combination))

    def test_constraints(self):
        """The goal of this test is to make sure constraints are correct."""
        with self.assertRaises(UserError, msg="can't change variants creation mode of attribute used on product"):
            self.ram_attribute.create_variant = 'no_variant'

        with self.assertRaises(UserError, msg="can't delete attribute used on product"):
            self.ram_attribute.unlink()

        with self.assertRaises(UserError, msg="can't change the attribute of an value used on product"):
            self.ram_32.attribute_id = self.hdd_attribute.id

        with self.assertRaises(UserError, msg="can't delete value used on product"):
            self.ram_32.unlink()

        with self.assertRaises(ValidationError, msg="can't have attribute without value on product"):
            self.env['product.template.attribute.line'].create({
                'product_tmpl_id': self.computer_case.id,
                'attribute_id': self.hdd_attribute.id,
                'value_ids': [(6, 0, [])],
            })

        with self.assertRaises(ValidationError, msg="value attribute must match line attribute"):
            self.env['product.template.attribute.line'].create({
                'product_tmpl_id': self.computer_case.id,
                'attribute_id': self.ram_attribute.id,
                'value_ids': [(6, 0, [self.ssd_256.id])],
            })

        with self.assertRaises(UserError, msg="can't change the attribute of an attribute line"):
            self.computer_ssd_attribute_lines.attribute_id = self.hdd_attribute.id

        with self.assertRaises(UserError, msg="can't change the product of an attribute line"):
            self.computer_ssd_attribute_lines.product_tmpl_id = self.computer_case.id

        with self.assertRaises(UserError, msg="can't change the value of a product template attribute value"):
            self.computer_ram_attribute_lines.product_template_value_ids[0].product_attribute_value_id = self.hdd_1

        with self.assertRaises(UserError, msg="can't change the product of a product template attribute value"):
            self.computer_ram_attribute_lines.product_template_value_ids[0].product_tmpl_id = self.computer_case.id

        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError, msg="can't have two values with the same name for the same attribute"):
            self.env['product.attribute.value'].create({
                'name': '32 GB',
                'attribute_id': self.ram_attribute.id,
            })

    def test_inactive_related_product_update(self):
        """
            Create a product and give it a product attribute then archive it, delete the product attribute,
            unarchive the product and check that the product is not related to the product attribute.
        """
        product_attribut = self.env['product.attribute'].create({
            'name': 'PA',
            'sequence': 1,
            'create_variant': 'no_variant',
        })
        a1 = self.env['product.attribute.value'].create({
            'name': 'pa_value',
            'attribute_id': product_attribut.id,
            'sequence': 1,
        })
        product = self.env['product.template'].create({
            'name': 'P1',
            'type': 'consu',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': product_attribut.id,
                'value_ids': [(6, 0, [a1.id])],
            })]
        })
        self.assertEqual(product_attribut.number_related_products, 1, 'The product attribute must have an associated product')
        product.action_archive()
        self.assertFalse(product.active, 'The product should be archived.')
        product.write({'attribute_line_ids': [[5, 0, 0]]})
        product.action_unarchive()
        self.assertTrue(product.active, 'The product should be unarchived.')
        self.assertEqual(product_attribut.number_related_products, 0, 'The product attribute must not have an associated product')
