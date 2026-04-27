# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestQualityCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_category_base = cls.env.ref('product.product_category_1')
        cls.product_category_1 = cls.env['product.category'].create({
            'name': 'Office furnitures',
            'parent_id': cls.product_category_base.id
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Office Chair',
            'categ_id': cls.product_category_1.id
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': 'Test Product',
            'categ_id': cls.product_category_base.parent_id.id
        })
        cls.product_3 = cls.env['product.product'].create({
            'name': 'Another Test Product',
            'categ_id': cls.product_category_base.parent_id.id
        })
        cls.product_4 = cls.env['product.product'].create({
            'name': 'Saleable Product',
            'categ_id': cls.product_category_base.id
        })
        cls.failure_location = cls.env['stock.location'].create({
            'name': 'Fail',
        })
        cls.product_tmpl_id = cls.product.product_tmpl_id.id
        cls.partner_id = cls.env['res.partner'].create({'name': 'A Test Partner'}).id
        cls.picking_type_id = cls.env.ref('stock.picking_type_in').id
        cls.location_id = cls.env.ref('stock.stock_location_suppliers').id
        cls.location_dest_id = cls.env.ref('stock.stock_location_stock').id
