# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon

class TestWebsiteSaleSubscriptionCommon(TestSubscriptionCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Subscription Company',
        })

        cls.current_website = cls.env['website'].create({
            'company_id': cls.company.id,
            'name': 'Test Website'
        })

        ProductTemplate = cls.env['product.template']
        ProductAttributeVal = cls.env['product.attribute.value']
        Pricing = cls.env['sale.subscription.pricing']
        Pricelist = cls.env['product.pricelist']

        # create product 1
        cls.sub_product = ProductTemplate.create({
            'name': 'Streaming SUB Weekly',
            'list_price': 0,
            'recurring_invoice': True,
        })
        Pricing.create([
            {
                'plan_id': cls.plan_week.id,
                'price': 5.0,
                'product_template_id': cls.sub_product.id,
            }
        ])

        # create product 2
        cls.sub_product_2 = ProductTemplate.create({
            'name': 'Streaming SUB Monthly',
            'list_price': 0,
            'recurring_invoice': True,
        })
        Pricing.create([
            {
                'plan_id': cls.plan_month.id,
                'price': 25.0,
                'product_template_id': cls.sub_product_2.id,
            }
        ])
        # create product 3
        cls.sub_product_3 = ProductTemplate.create({
            'name': 'Streaming SUB Yearly',
            'list_price': 0,
            'recurring_invoice': True,
        })
        cls.pricelist_111 = Pricelist.create({
            'name': 'Pricelist111',
            'selectable': True,
            'company_id': False,
        })
        cls.pricelist_222 = Pricelist.create({
            'name': 'Pricelist222',
            'selectable': True,
            'company_id': False,
        })
        Pricing.create([
            {
                'plan_id': cls.plan_year.id,
                'price': 111.0,
                'product_template_id': cls.sub_product_3.id,
                'pricelist_id': cls.pricelist_111.id,
            }
        ])
        Pricing.create([
            {
                'plan_id': cls.plan_year.id,
                'price': 222.0,
                'product_template_id': cls.sub_product_3.id,
                'pricelist_id': cls.pricelist_222.id,
            }
        ])

        # create product with variants
        product_attribute = cls.env['product.attribute'].create({'name': 'Color'})
        product_attribute_val1 = ProductAttributeVal.create({
            'name': 'Black',
            'attribute_id': product_attribute.id
        })
        product_attribute_val2 = ProductAttributeVal.create({
            'name': 'White',
            'attribute_id': product_attribute.id
        })

        cls.sub_with_variants = ProductTemplate.create({
            'recurring_invoice': True,
            'type': 'service',
            'name': 'Variant Products',
        })

        cls.sub_with_variants.attribute_line_ids = [(Command.create({
            'attribute_id': product_attribute.id,
            'value_ids': [Command.set([product_attribute_val1.id, product_attribute_val2.id])],
        }))]

        pricing1 = Pricing.create({
            'plan_id': cls.plan_week.id,
            'price': 10,
            'product_template_id': cls.sub_with_variants.id,
            'product_variant_ids': [Command.link(cls.sub_with_variants.product_variant_ids[0].id)],
        })

        pricing2 = Pricing.create({
            'plan_id': cls.plan_month.id,
            'price': 25,
            'product_template_id': cls.sub_with_variants.id,
            'product_variant_ids': [Command.link(cls.sub_with_variants.product_variant_ids[-1].id)],
        })

        cls.sub_with_variants.write({
            'product_subscription_pricing_ids': [Command.set([pricing1.id, pricing2.id])]
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'partner_a',
        })
