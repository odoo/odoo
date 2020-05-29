# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, common


@tagged('post_install', '-at_install')
class TestMatrixCommon(common.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Prepare relevant test data
        # This is not included in demo data to avoid useless noise
        product_attributes = cls.env['product.attribute'].create([{
            'name': 'PA1',
            'create_variant': 'always',
            'sequence': 1
        }, {
            'name': 'PA2',
            'create_variant': 'always',
            'sequence': 2
        }, {
            'name': 'PA3',
            'create_variant': 'dynamic',
            'sequence': 3
        }, {
            'name': 'PA4',
            'create_variant': 'no_variant',
            'sequence': 4
        }])

        cls.env['product.attribute.value'].create([{
            'name': 'PAV' + str(product_attribute.sequence) + str(i),
            'attribute_id': product_attribute.id
        } for i in range(1, 3) for product_attribute in product_attributes])

        cls.matrix_template = cls.env['product.template'].create({
            'name': "Matrix",
            'type': "consu",
            'uom_id': cls.env.ref("uom.product_uom_unit").id,
            'uom_po_id': cls.env.ref("uom.product_uom_unit").id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)]
            }) for attribute in product_attributes],
        })
