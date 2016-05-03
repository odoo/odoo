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
        categ_unit = cls.env.ref('product.product_uom_categ_unit')
        weight_unit = cls.env.ref('product.product_uom_categ_kgm')
        cls.uom_unit = Uom.create({
            'name': 'TestUnit',
            'category_id': categ_unit.id,
            'factor_inv': 1.0,
            'factor': 1.0,
            'uom_type': 'reference',
            'rounding': 0.000001})
        cls.uom_kunit = Uom.create({
            'name': 'KTestUnit',
            'category_id': categ_unit.id,
            'factor_inv': 1000.0,
            'factor': 0.001,
            'uom_type': 'bigger',
            'rounding': 0.001})
        cls.uom_munit = Uom.create({
            'name': 'mTestUnit',
            'category_id': categ_unit.id,
            'factor_inv': 0.001,
            'factor': 1000.0,
            'uom_type': 'smaller',
            'rounding': 0.001})
        cls.uom_weight = Uom.create({
            'name': 'TestWeight',
            'category_id': weight_unit.id,
            'factor_inv': 1.0,
            'factor': 1.0,
            'uom_type': 'reference',
            'rounding': 0.000001
        })
        Product = cls.env['product.product']
        cls.product_1 = Product.create({
            'name': 'TestProduct 1',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})
        cls.product_2 = Product.create({
            'name': 'TestProduct 2',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})
        cls.product_3 = Product.create({
            'name': 'TestProduct 3 (KTestUnit)',
            'uom_id': cls.uom_kunit.id,
            'uom_po_id': cls.uom_kunit.id})
        cls.product_4 = Product.create({
            'name': 'TestProduct 4 (mTestUnit)',
            'uom_id': cls.uom_munit.id,
            'uom_po_id': cls.uom_munit.id})
