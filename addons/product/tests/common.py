# -*- coding: utf-8 -*-

from odoo.tests import common


class TestProductCommon(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestProductCommon, cls).setUpClass()

        # Customer related data
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Julia Agrolait',
            'email': 'julia@agrolait.example.com',
        })

        # Product environment related data
        Uom = cls.env['product.uom']
        cls.uom_unit = cls.env.ref('product.product_uom_unit')
        cls.uom_dozen = cls.env.ref('product.product_uom_dozen')
        cls.uom_dunit = Uom.create({
            'name': 'DeciUnit',
            'category_id': cls.uom_unit.category_id.id,
            'factor_inv': 0.1,
            'factor': 10.0,
            'uom_type': 'smaller',
            'rounding': 0.001})
        cls.uom_weight = cls.env.ref('product.product_uom_kgm')
        Product = cls.env['product.product']
        cls.product_0 = Product.create({
            'name': 'Work',
            'type': 'service',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})
        cls.product_1 = Product.create({
            'name': 'Courage',
            'type': 'consu',
            'default_code': 'PROD-1',
            'uom_id': cls.uom_dunit.id,
            'uom_po_id': cls.uom_dunit.id})

        cls.product_2 = Product.create({
            'name': 'Wood',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})
        cls.product_3 = Product.create({
            'name': 'Stone',
            'uom_id': cls.uom_dozen.id,
            'uom_po_id': cls.uom_dozen.id})

        cls.product_4 = Product.create({
            'name': 'Stick',
            'uom_id': cls.uom_dozen.id,
            'uom_po_id': cls.uom_dozen.id})
        cls.product_5 = Product.create({
            'name': 'Stone Tools',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})

        cls.product_6 = Product.create({
            'name': 'Door',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})

        cls.prod_att_1 = cls.env['product.attribute'].create({'name': 'Color'})
        cls.prod_attr1_v1 = cls.env['product.attribute.value'].create({'name': 'red', 'attribute_id': cls.prod_att_1.id})
        cls.prod_attr1_v2 = cls.env['product.attribute.value'].create({'name': 'blue', 'attribute_id': cls.prod_att_1.id})

        cls.product_7_template = cls.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': cls.prod_att_1.id,
            })]
        })
        cls.product_7 = Product.create({
            'product_tmpl_id': cls.product_7_template.id,
        })
        cls.product_7_1 = Product.create({
            'product_tmpl_id': cls.product_7_template.id,
            'attribute_value_ids': [(6, 0, [cls.prod_attr1_v1.id])],
        })
        cls.product_7_2 = Product.create({
            'product_tmpl_id': cls.product_7_template.id,
            'attribute_value_ids': [(6, 0, [cls.prod_attr1_v2.id])],
        })

        cls.product_8 = Product.create({
            'name': 'House',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})

        cls.product_9 = Product.create({
            'name': 'Paper',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})

        cls.product_10 = Product.create({
            'name': 'Stone',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})
