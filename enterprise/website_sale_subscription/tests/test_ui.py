# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase, tagged
from .common import TestWebsiteSaleSubscriptionCommon

@tagged('-at_install', 'post_install')
class TestUi(HttpCase, TestWebsiteSaleSubscriptionCommon):

    def test_website_sale_subscription_ui(self):
        self.start_tour("/odoo", 'shop_buy_subscription_product', login='admin')

    def test_website_sale_subscription_product_variants(self):
        reccuring_product = self.env['product.template'].create({
            'recurring_invoice': True,
            'type': 'service',
            'name': 'Reccuring product',
        })
        product_attribute = self.env['product.attribute'].create({'name': 'periods'})

        product_attribute_val1 = self.env['product.attribute.value'].create({
            'name': 'Monthly',
            'attribute_id': product_attribute.id
        })
        product_attribute_val2 = self.env['product.attribute.value'].create({
            'name': '2 Months',
            'attribute_id': product_attribute.id
        })
        product_attribute_val3 = self.env['product.attribute.value'].create({
            'name': 'Yearly',
            'attribute_id': product_attribute.id
        })

        reccuring_product.attribute_line_ids = [(Command.create({
            'attribute_id': product_attribute.id,
            'value_ids': [Command.set([product_attribute_val1.id, product_attribute_val2.id, product_attribute_val3.id])],
        }))]

        pricing1 = self.env['sale.subscription.pricing'].create({
            'plan_id': self.plan_month.id,
            'price': 90,
            'product_template_id': reccuring_product.id,
            'product_variant_ids': [Command.link(reccuring_product.product_variant_ids[-3].id)],
        })
        pricing2 = self.env['sale.subscription.pricing'].create({
            'plan_id': self.plan_2_month.id,
            'price': 160,
            'product_template_id': reccuring_product.id,
            'product_variant_ids': [Command.link(reccuring_product.product_variant_ids[-2].id)],
        })
        pricing3 = self.env['sale.subscription.pricing'].create({
            'plan_id': self.plan_year.id,
            'price': 1000,
            'product_template_id': reccuring_product.id,
            'product_variant_ids': [Command.link(reccuring_product.product_variant_ids[-1].id)],
        })

        reccuring_product.write({
            'product_subscription_pricing_ids': [Command.set([pricing1.id, pricing2.id, pricing3.id])]
        })

        self.start_tour(reccuring_product.website_url, 'sale_subscription_product_variants', login='admin')

    def test_website_sale_subscription_product_variant_add_to_cart(self):
        product_attribute = self.env['product.attribute'].create({'name': 'Color'})
        product_attribute_val1 = self.env['product.attribute.value'].create({
            'name': 'Black',
            'attribute_id': product_attribute.id
        })
        product_attribute_val2 = self.env['product.attribute.value'].create({
            'name': 'White',
            'attribute_id': product_attribute.id
        })

        self.product_tmpl_2.attribute_line_ids = [(Command.create({
            'attribute_id': product_attribute.id,
            'value_ids': [
                Command.set([product_attribute_val1.id, product_attribute_val2.id])],
        }))]

        self.product_tmpl_2.write({
            'product_subscription_pricing_ids': [Command.set([self.pricing_month.id, self.pricing_year.id])]
        })
        self.start_tour(self.product_tmpl_2.website_url, 'sale_subscription_add_to_cart', login='admin')
