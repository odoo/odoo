# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestsCommon(common.TransactionCase):

    def setUp(self):
        super(TestsCommon, self).setUp()

        self.partner_pizza_inn = self.env['res.partner'].create({
            'name': 'Pizza Inn',
        })

        self.supplier_pizza_inn = self.env['lunch.supplier'].create({
            'partner_id': self.partner_pizza_inn.id,
            'send_by': 'mail',
            'automatic_email_send': True,
            'automatic_email_time': 11,
            'recurrency': 'reccurent',
            'recurrency_from': 8,
            'recurrency_to': 23,
            'recurrency_monday': True,
            'recurrency_tuesday': True,
            'recurrency_wednesday': True,
            'recurrency_thursday': True,
            'recurrency_friday': True,
        })

        self.partner_coin_gourmand = self.env['res.partner'].create({
            'name': 'Coin Gourmand',
        })

        self.supplier_coin_gourmand = self.env['lunch.supplier'].create({
            'partner_id': self.partner_coin_gourmand.id,
            'send_by': 'phone',
            'recurrency': 'reccurent',
            'recurrency_from': 8,
            'recurrency_to': 23,
            'recurrency_monday': True,
            'recurrency_tuesday': True,
            'recurrency_wednesday': True,
            'recurrency_thursday': True,
            'recurrency_friday': True,
        })

        self.category_pizza = self.env['lunch.product.category'].create({
            'name': 'Pizza',
        })

        self.category_sandwich = self.env['lunch.product.category'].create({
            'name': 'Sandwich',
        })

        self.product_pizza = self.env['lunch.product'].create({
            'name': 'Pizza',
            'category_id': self.category_pizza.id,
            'price': 9,
            'supplier_id': self.supplier_pizza_inn.id,
        })

        self.product_sandwich_tuna = self.env['lunch.product'].create({
            'name': 'Tuna Sandwich',
            'category_id': self.category_sandwich.id,
            'price': 3,
            'supplier_id': self.supplier_coin_gourmand.id,
        })

        self.topping_olives = self.env['lunch.product'].create({
            'name': 'Olives',
            'price': 0.3,
            'supplier_id': self.supplier_pizza_inn.id,
            'is_topping': True,
        })
