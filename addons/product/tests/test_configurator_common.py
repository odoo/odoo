# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestProductConfiguratorCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setup attributes and attributes values
        cls.product_attribute_1 = cls.env['product.attribute'].create({
            'name': 'Legs',
            'sequence': 10,
        })
        cls.product_attribute_value_1 = cls.env['product.attribute.value'].create({
            'name': 'Steel',
            'attribute_id': cls.product_attribute_1.id,
            'sequence': 1,
        })
        cls.product_attribute_value_2 = cls.env['product.attribute.value'].create({
            'name': 'Aluminium',
            'attribute_id': cls.product_attribute_1.id,
            'sequence': 2,
        })
        product_attribute_2 = cls.env['product.attribute'].create({
            'name': 'Color',
            'display_type': 'color',
            'sequence': 20,
        })
        product_attribute_value_3 = cls.env['product.attribute.value'].create({
            'name': 'White',
            'attribute_id': product_attribute_2.id,
            'html_color': '#FFFFFF',
            'sequence': 1,
        })
        product_attribute_value_4 = cls.env['product.attribute.value'].create({
            'name': 'Black',
            'attribute_id': product_attribute_2.id,
            'html_color': '#000000',
            'sequence': 2,
        })

        # Create product template
        cls.product_product_custo_desk = cls.env['product.template'].create({
            'name': 'Customizable Desk (TEST)',
            'standard_price': 500.0,
            'list_price': 750.0,
        })

        # Generate variants
        cls.env['product.template.attribute.line'].create([{
            'product_tmpl_id': cls.product_product_custo_desk.id,
            'attribute_id': cls.product_attribute_1.id,
            'value_ids': [(4, cls.product_attribute_value_1.id), (4, cls.product_attribute_value_2.id)],
        }, {
            'product_tmpl_id': cls.product_product_custo_desk.id,
            'attribute_id': product_attribute_2.id,
            'value_ids': [(4, product_attribute_value_3.id), (4, product_attribute_value_4.id)],

        }])

        # Add a Custom attribute
        product_attribute_value_custom = cls.env['product.attribute.value'].create({
            'name': 'Custom',
            'attribute_id': cls.product_attribute_1.id,
            'sequence': 3,
            'is_custom': True
        })
        cls.product_product_custo_desk.attribute_line_ids[0].write({'value_ids': [(4, product_attribute_value_custom.id)]})

        # Disable the aluminium + black product
        cls.product_product_custo_desk.product_variant_ids[3].active = False
