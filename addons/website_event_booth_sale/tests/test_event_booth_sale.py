# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.tests import HttpCase
from odoo.tests.common import tagged



@tagged('post_install', '-at_install')
class TestWebsiteEventBoothSale(HttpCase, TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['website'].sudo().search([]).show_line_subtotals_tax_selection = 'tax_included'
        cls.tax = cls.env['account.tax'].sudo().create({
            'name': 'Tax 10',
            'amount': 10,
        })
        cls.booth_product = cls.env['product.product'].create({
            'name': 'Test Booth Product',
            'description_sale': 'Mighty Booth Description',
            'list_price': 20,
            'standard_price': 60.0,
            'taxes_id': [(6, 0, [cls.tax.id])],
            'detailed_type': 'event_booth',
        })
        cls.event_booth_category = cls.env['event.booth.category'].create({
            'name': 'Standard',
            'description': '<p>Standard</p>',
            'product_id': cls.booth_product.id,
            'price': 100.0,
        })
        cls.event_type = cls.env['event.type'].create({
            'name': 'Booth Type',
            'event_type_booth_ids': [
                Command.create({
                    'name': 'Standard 1',
                    'booth_category_id': cls.event_booth_category.id,
                }),
                Command.create({
                    'name': 'Standard 2',
                    'booth_category_id': cls.event_booth_category.id,
                }),
                Command.create({
                    'name': 'Standard 3',
                    'booth_category_id': cls.event_booth_category.id,
                }),
            ],
        })
        cls.env['event.event'].create({
            'name': 'Test Event Booths',
            'event_type_id': cls.event_type.id,
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_published': True,
            'website_menu': True,
            'booth_menu': True,
        })

    def test_tour(self):
        self.env['product.pricelist'].sudo().search([]).action_archive()
        self.start_tour('/event', 'website_event_booth_tour', login='portal')

    def test_booth_pricelists_different_currencies(self):
        self.start_tour("/web", 'event_booth_sale_pricelists_different_currencies', login='admin')
