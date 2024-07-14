# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestWebsiteSaleRentingCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Renting Company',
            'renting_forbidden_sat': True,
            'renting_forbidden_sun': True,
        })
        cls.computer = cls.env['product.product'].create({
            'name': 'Computer',
            'list_price': 2000,
            'rent_ok': True,
        })
        recurrence_hour = cls.env['sale.temporal.recurrence'].sudo().create({'duration': 1, 'unit': 'hour'})
        recurrence_5_hour = cls.env['sale.temporal.recurrence'].sudo().create({'duration': 5, 'unit': 'hour'})
        cls.env['product.pricing'].create([
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
                'product_template_id': cls.computer.product_tmpl_id.id,
            }, {
                'recurrence_id': recurrence_5_hour.id,
                'price': 15.0,
                'product_template_id': cls.computer.product_tmpl_id.id,
            },
        ])
        cls.partner = cls.env['res.partner'].create({
            'name': 'partner_a',
        })

    def setUp(self):
        super().setUp()
        # Allow renting on any day for tests, avoids unexpected error
        self.env.company.renting_forbidden_mon = False
        self.env.company.renting_forbidden_tue = False
        self.env.company.renting_forbidden_wed = False
        self.env.company.renting_forbidden_thu = False
        self.env.company.renting_forbidden_fri = False
        self.env.company.renting_forbidden_sat = False
        self.env.company.renting_forbidden_sun = False
