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

        # Units of Measure
        Uom = cls.env['uom.uom']
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.uom_dunit = Uom.create({
            'name': 'DeciUnit',
            'category_id': cls.uom_unit.category_id.id,
            'factor_inv': 0.1,
            'factor': 10.0,
            'uom_type': 'smaller',
            'rounding': 0.001
        })
        cls.uom_kgm = cls.env.ref('uom.product_uom_kgm')
        cls.uom_ton = cls.env.ref('uom.product_uom_ton')

        # Products
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
        cls.prod_attr1_v1 = cls.env['product.attribute.value'].create({'name': 'red', 'attribute_id': cls.prod_att_1.id, 'sequence': 1})
        cls.prod_attr1_v2 = cls.env['product.attribute.value'].create({'name': 'blue', 'attribute_id': cls.prod_att_1.id, 'sequence': 2})
        cls.prod_attr1_v3 = cls.env['product.attribute.value'].create({'name': 'green', 'attribute_id': cls.prod_att_1.id, 'sequence': 3})

        cls.product_7_template = cls.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': cls.prod_att_1.id,
                'value_ids': [(6, 0, [cls.prod_attr1_v1.id, cls.prod_attr1_v2.id, cls.prod_attr1_v3.id])]
            })]
        })

        cls.product_7_attr1_v1 = cls.product_7_template.attribute_line_ids[0].product_template_value_ids[0]
        cls.product_7_attr1_v2 = cls.product_7_template.attribute_line_ids[0].product_template_value_ids[1]
        cls.product_7_attr1_v3 = cls.product_7_template.attribute_line_ids[0].product_template_value_ids[2]

        cls.product_7_1 = cls.product_7_template._get_variant_for_combination(cls.product_7_attr1_v1)
        cls.product_7_2 = cls.product_7_template._get_variant_for_combination(cls.product_7_attr1_v2)
        cls.product_7_3 = cls.product_7_template._get_variant_for_combination(cls.product_7_attr1_v3)

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

        cls.env['product.pricelist'].search([]).active = False

        cls.public_pricelist = cls.env['product.pricelist'].create({
            "name": "Public Pricelist",
            "sequence": 1,
        })


class TestAttributesCommon(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestAttributesCommon, cls).setUpClass()

        # create 10 attributes with 10 values each
        cls.att_names = "ABCDEFGHIJ"
        cls.attributes = cls.env['product.attribute'].create([{
                'name': name,
                'create_variant': 'no_variant',
                'value_ids': [(0, 0, {'name': n}) for n in range(10)]
            } for name in cls.att_names
        ])

class TestPricelistCommon(TestProductCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPricelistCommon, cls).setUpClass()

        cls.partner_2 = cls.env['res.partner'].create({'name': 'Ready Mat'})
        cls.partner_3 = cls.env['res.partner'].create({'name': 'Wood Corner'})
        # VFE TODO set a different property_product_pricelist on those two partners

        # Setup currencies
        cls.currency_yuan = cls.env.ref("base.CNY")
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.currency_usd = cls.env.ref("base.USD")

        (cls.currency_yuan + cls.currency_eur + cls.currency_usd).active = True

        # Ensure all tests are done in consistend currency.
        cls.env.company.currrency_id = cls.currency_usd

        # Setup uoms

        uom_unit_category_id = cls.uom_unit.category_id.id
        # cls.uom_unit already defined by TestProductCommon
        cls.uom_half = cls.env["uom.uom"].create({
            "name": "Half",
            "factor": 2,
            "uom_type": "smaller",
            "category_id": uom_unit_category_id,
        })
        cls.uom_trio = cls.env["uom.uom"].create({
            "name": "Trio",
            "factor_inv": 3,
            "uom_type": "bigger",
            "category_id": uom_unit_category_id,
        })

        # Setup pricelists

        cls.empty_pricelist = cls.public_pricelist
        # VFE TODO fix public_pricelist currency to USD?

        cls.basic_pricelist = cls.env['product.pricelist'].create({
            "name": "Basic Test",
            "currency_id": cls.currency_eur.id,
            # TODO rules on product, variants, categories
            # fixed, formulas and discounts
        })

        # cls.advanced_pricelist = cls.env['product.pricelist'].create({
        #     "name": "Advanced Test",
        #     "currency_id": cls.currency_3.id,
        #     "item_ids": [(0, 0, {
        #         "applied_on": "3_global/2_product_category/1_product/0_product_variant",
        #         #categ_id,product_id,product_tmpl_id
        #         "base": "list_price/standard_price/pricelist",
        #         "compute_price": "percentage/formula",
        #     })]
        # })
        #
        # cls.pricelist_chain_3 = cls.env['product.pricelist'].create({
        #     "name": "Chained Pricelist - End",
        #     "currency_id": cls.currency_3.id,
        #     "item_ids": [(0, 0, {
        #         "applied_on": "3_global/2_product_category/1_product/0_product_variant",
        #         #categ_id,product_id,product_tmpl_id
        #         "base": "list_price/standard_price/pricelist",
        #         "compute_price": "percentage",
        #     })]
        # })
        #
        # cls.pricelist_chain_2 = cls.env['product.pricelist'].create({
        #     "name": "Chained Pricelist - Center",
        #     "currency_id": cls.currency_3.id,
        #     "item_ids": [(0, 0, {
        #         "applied_on": "3_global/2_product_category/1_product/0_product_variant",
        #         #categ_id,product_id,product_tmpl_id
        #         "base": "pricelist",
        #         "compute_price": "formula",
        #     })]
        # })
        #
        # cls.pricelist_chain_1 = cls.env['product.pricelist'].create({
        #     "name": "Chained Pricelist - Begin",
        #     "currency_id": cls.currency_3.id,
        #     "item_ids": [],
        # })

        # VFE TODO set rules only for some products / categories in TestProductCommon
        # VFE TODO rules for specific dates
        # VFE TODO rules for specific quantities
        # VFE TODO discount / no discount
        # VFE TODO in website : country groups tests ?

class TestNoPricelistCommon(TestProductCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPricelistCommon, cls).setUpClass()

        cls.public_pricelist.active = False
        cls.env['product.pricelist'].search([]).active = False
