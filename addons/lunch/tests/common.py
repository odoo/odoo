# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestsCommon(common.TransactionCase):

    def setUp(self):
        super(TestsCommon, self).setUp()

        self.location_office_1 = self.env['lunch.location'].create({
            'name' : 'Farm 1',
        })

        self.location_office_2 = self.env['lunch.location'].create({
            'name': 'Farm 2',
        })

        self.partner_pizza_inn = self.env['res.partner'].create({
            'name': 'Pizza Inn',
        })

        self.supplier_pizza_inn = self.env['lunch.supplier'].create({
            'partner_id': self.partner_pizza_inn.id,
            'send_by': 'mail',
            'automatic_email_time': 11,
            'available_location_ids': [
                (6, 0, [self.location_office_1.id, self.location_office_2.id])
            ],
        })

        self.partner_coin_gourmand = self.env['res.partner'].create({
            'name': 'Coin Gourmand',
        })

        self.supplier_coin_gourmand = self.env['lunch.supplier'].create({
            'partner_id': self.partner_coin_gourmand.id,
            'send_by': 'phone',
            'available_location_ids': [
                (6, 0, [self.location_office_1.id, self.location_office_2.id])
            ],
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

        self.topping_olives = self.env['lunch.topping'].create({
            'name': 'Olives',
            'price': 0.3,
            'category_id': self.category_pizza.id,
        })

        self.env['lunch.cashmove'].create({
            'amount': 100,
        })
