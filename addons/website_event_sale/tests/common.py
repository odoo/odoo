# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.fields import Datetime
from odoo.tests.common import TransactionCase


class TestWebsiteEventSaleCommon(TransactionCase):

    def setUp(self):
        super().setUp()

        self.event = self.env['event.event'].create({
            'date_begin': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 07:00:00'),
            'date_end': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 16:30:00'),
            'name': 'Pycon',
            'user_id': self.env.ref('base.user_admin').id,
            'website_published': True,
        })
        self.ticket = self.env['event.event.ticket'].create([{
            'event_id': self.event.id,
            'name': 'Standard',
            'product_id': self.env.ref('event_sale.product_product_event').id,
            'price': 100,
        }])
        self.currency_test = self.env['res.currency'].create({
            'name': 'eventX',
            'rate': 10,
            'rounding': 0.01,
            'symbol': 'EX',
        })
        self.partner = self.env['res.partner'].create({'name': 'test'})
        self.new_company = self.env['res.company'].create({
            'currency_id': self.env.ref('base.EUR').id,
            'name': 'Great Company EUR',
            'partner_id': self.partner.id,
        })
        self.env['res.currency.rate'].create({
            'company_id': self.new_company.id,
            'currency_id': self.currency_test.id,
            'name': '2022-01-01',
            'rate': 10,
        })

        self.current_website = self.env['website'].get_current_website()
        self.pricelist = self.current_website.get_current_pricelist()

        self.so = self.env['sale.order'].create({
            'company_id': self.new_company.id,
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id,
        })
