# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from freezegun import freeze_time

@tagged('-at_install', 'post_install')
class TestUi(HttpCase):
    def test_01_ui(self):
        self.location_office = self.env['lunch.location'].create({
            'name' : 'Farm 1',
        })

        self.partner_pizza_inn = self.env['res.partner'].create({
            'name': 'Pizza Inn',
        })

        self.supplier_pizza_inn = self.env['lunch.supplier'].create({
            'partner_id': self.partner_pizza_inn.id,
            'send_by': 'phone',
            'mon': True,
            'tue': True,
            'wed': True,
            'thu': True,
            'fri': True,
            'sat': True,
            'sun': True,
            'available_location_ids': [
                (6, 0, [self.location_office.id])
            ],
        })

        self.category_pizza = self.env['lunch.product.category'].create({
            'name': 'Test category',
        })

        self.product_pizza = self.env['lunch.product'].create({
            'name': "Aaron's Pizza",
            'category_id': self.category_pizza.id,
            'price': 9,
            'supplier_id': self.supplier_pizza_inn.id,
        })

        user_admin = self.env.ref('base.user_admin')
        self.env['lunch.cashmove'].create({
            'user_id': user_admin.id,
            'amount': 10,
        })

        with freeze_time("2022-04-19 10:00"):
            self.start_tour("/", 'order_lunch_tour', login='admin', timeout=180)
