# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestProductAttributeValueConfig(TransactionCase):
    def setUp(self):
        super(TestProductAttributeValueConfig, self).setUp()

        self.computer = self.env['product.template'].create({
            'name': 'Super Computer'
        })

        self._add_ssd_attribute()
        self._add_ram_attribute()
        self._add_hdd_attribute()

        self.computer.create_variant_ids()

        self.computer_case = self.env['product.template'].create({
            'name': 'Super Computer Case'
        })

        self._add_size_attribute()

        self.computer_case.create_variant_ids()

    def test_product_template_attribute_values_creation(self):
        self.assertEqual(len(self.computer_ssd_attribute_lines.product_template_value_ids), 2,
            'Product attribute values (ssd) were not automatically created')
        self.assertEqual(len(self.computer_ram_attribute_lines.product_template_value_ids), 3,
            'Product attribute values (ram) were not automatically created')
        self.assertEqual(len(self.computer_hdd_attribute_lines.product_template_value_ids), 3,
            'Product attribute values (hdd) were not automatically created')
        self.assertEqual(len(self.computer_case_size_attribute_lines.product_template_value_ids), 3,
            'Product attribute values (size) were not automatically created')

    def test_product_filtered_exclude_for(self):
        """
            Super Computer has 18 variants total (2 ssd * 3 ram * 3 hdd)
            RAM 16 excudes HDD 1, that matches 2 variants:
            - SSD 256 RAM 16 HDD 1
            - SSD 512 RAM 16 HDD 1

            => There has to be 16 variants left when filtered
        """
        self._add_ram_exclude_for()
        self.assertEqual(len(self.computer.get_filtered_variants()), 16)
        self.assertFalse(self._get_variant_for_attribute_values(self.computer, [self.ssd_256, self.ram_16, self.hdd_1]))
        self.assertFalse(self._get_variant_for_attribute_values(self.computer, [self.ssd_512, self.ram_16, self.hdd_1]))

    def test_children_product_filtered_exclude_for(self):
        """
            Super Computer Case has 3 variants total (3 size)
            Reference product Computer with HDD 4 excludes Size M
            The following variant will be excluded:
            - Size M

            => There has to be 2 variants left when filtered
        """

        self._add_hdd_excludes_computer_case()
        hdd_4_variant = self.computer.product_variant_ids.filtered(
            lambda variant: self.hdd_4 in variant.product_template_attribute_value_ids.mapped('product_attribute_value_id'))[0]
        self.assertEqual(len(self.computer_case.get_filtered_variants(hdd_4_variant)), 2)
        self.assertFalse(self._get_variant_for_attribute_values(self.computer_case, [self.size_m], hdd_4_variant))

    def _add_ssd_attribute(self):
        self.ssd_attribute = self.env['product.attribute'].create({'name': 'Memory'})
        self.ssd_256 = self.env['product.attribute.value'].create({
            'name': '256 GB',
            'attribute_id': self.ssd_attribute.id
        })
        self.ssd_512 = self.env['product.attribute.value'].create({
            'name': '512 GB',
            'attribute_id': self.ssd_attribute.id
        })
        self.computer_ssd_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.computer.id,
            'attribute_id': self.ssd_attribute.id,
            'value_ids': [(6, 0, [self.ssd_256.id, self.ssd_512.id])]
        })

    def _add_ram_attribute(self):
        self.ram_attribute = self.env['product.attribute'].create({'name': 'RAM'})
        self.ram_8 = self.env['product.attribute.value'].create({
            'name': '8 GB',
            'attribute_id': self.ram_attribute.id
        })
        self.ram_16 = self.env['product.attribute.value'].create({
            'name': '16 GB',
            'attribute_id': self.ram_attribute.id
        })
        self.ram_32 = self.env['product.attribute.value'].create({
            'name': '32 GB',
            'attribute_id': self.ram_attribute.id
        })
        self.computer_ram_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.computer.id,
            'attribute_id': self.ram_attribute.id,
            'value_ids': [(6, 0, [self.ram_8.id, self.ram_16.id, self.ram_32.id])]
        })

    def _add_hdd_attribute(self):
        self.hdd_attribute = self.env['product.attribute'].create({'name': 'HDD'})
        self.hdd_1 = self.env['product.attribute.value'].create({
            'name': '1 To',
            'attribute_id': self.hdd_attribute.id
        })
        self.hdd_2 = self.env['product.attribute.value'].create({
            'name': '2 To',
            'attribute_id': self.hdd_attribute.id
        })
        self.hdd_4 = self.env['product.attribute.value'].create({
            'name': '4 To',
            'attribute_id': self.hdd_attribute.id
        })
        self.computer_hdd_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.computer.id,
            'attribute_id': self.hdd_attribute.id,
            'value_ids': [(6, 0, [self.hdd_1.id, self.hdd_2.id, self.hdd_4.id])]
        })

    def _add_ram_exclude_for(self):
        self.ram_16_excludes_hdd_1 = self.env['product.template.attribute.exclusion'].create({
            'product_tmpl_id': self.computer.id,
            'value_ids': [(6, 0, [self._get_product_value_id(self.computer_hdd_attribute_lines, self.hdd_1).id])]
        })
        self._get_product_value_id(self.computer_ram_attribute_lines, self.ram_16).update({
            'exclude_for': [(6, 0, [self.ram_16_excludes_hdd_1.id])]
        })

    def _add_size_attribute(self):
        self.size_attribute = self.env['product.attribute'].create({'name': 'Size'})
        self.size_m = self.env['product.attribute.value'].create({
            'name': 'M',
            'attribute_id': self.size_attribute.id
        })
        self.size_l = self.env['product.attribute.value'].create({
            'name': 'L',
            'attribute_id': self.size_attribute.id
        })
        self.size_xl = self.env['product.attribute.value'].create({
            'name': 'XL',
            'attribute_id': self.size_attribute.id
        })
        self.computer_case_size_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.computer_case.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [(6, 0, [self.size_m.id, self.size_l.id, self.size_xl.id])]
        })

    def _add_hdd_excludes_computer_case(self):
        self.hdd_4_excludes_computer_case_m = self.env['product.template.attribute.exclusion'].create({
            'product_tmpl_id': self.computer_case.id,
            'value_ids': [(6, 0, [self._get_product_value_id(self.computer_case_size_attribute_lines, self.size_m).id])]
        })
        self._get_product_value_id(self.computer_hdd_attribute_lines, self.hdd_4).update({
            'exclude_for': [(6, 0, [self.hdd_4_excludes_computer_case_m.id])]
        })

    def _get_product_value_id(self, product_template_attribute_lines, product_attribute_value):
        return product_template_attribute_lines.product_template_value_ids.filtered(
            lambda product_value_id: product_value_id.product_attribute_value_id == product_attribute_value)[0]

    def _get_variant_for_attribute_values(self, product, attribute_values, reference_product=None):
        return product.get_filtered_variants(reference_product).filtered(
            lambda variant:
            all(attribute_value in variant.attribute_value_ids for attribute_value in attribute_values))
