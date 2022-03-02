# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.fields import Datetime
from odoo.tests.common import TransactionCase


class TestWebsiteEventSaleCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestWebsiteEventSaleCommon, cls).setUpClass()

        cls.env.ref('base.USD').write({'active': False})
        cls.currency_test = cls.env['res.currency'].create({
            'name': 'eventX',
            'rate': 10,
            'rounding': 0.01,
            'symbol': 'EX',
        })

        cls.partner = cls.env['res.partner'].create({'name': 'test'})
        cls.new_company = cls.env['res.company'].create({
            'currency_id': cls.env.ref('base.EUR').id,
            'name': 'Great Company EUR',
            'partner_id': cls.partner.id,
        })
        cls.env['res.currency.rate'].create({
            'company_id': cls.new_company.id,
            'currency_id': cls.currency_test.id,
            'name': '2022-01-01',
            'rate': 10,
        })

        cls.product_event = cls.env['product.product'].create({
            'company_id': cls.new_company.id,
            'currency_id': cls.env.ref('base.EUR').id,
            'detailed_type': 'event',
            'list_price': 100,
            'name': 'Event Registration No Company Assigned',
        })

        cls.event = cls.env['event.event'].create({
            'date_begin': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 07:00:00'),
            'date_end': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 16:30:00'),
            'name': 'Pycon',
            'user_id': cls.env.ref('base.user_admin').id,
            'website_published': True,
        })
        cls.ticket = cls.env['event.event.ticket'].create([{
            'event_id': cls.event.id,
            'name': 'Standard',
            'product_id': cls.product_event.id,
            'price': 100,
        }])

        cls.current_website = cls.env['website'].get_current_website()
        cls.current_website.company_id = cls.new_company
        cls.pricelist = cls.current_website.get_current_pricelist()

        cls.so = cls.env['sale.order'].create({
            'company_id': cls.new_company.id,
            'partner_id': cls.partner.id,
            'pricelist_id': cls.pricelist.id,
        })
