# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.fields import Command
from odoo.tests import HttpCase, tagged, loaded_demo_data

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestUi(HttpCase):
    def setUp(self):
        super(TestUi, self).setUp()
        # create a Chair floor protection product
        self.env['product.product'].create({
            'name': 'Chair floor protection',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000,
        })
        # create a Customizable Desk product
        self.env['product.product'].create({
            'name': 'Customizable Desk',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000,
        })
        # create a Warranty product
        self.env['product.product'].create({
            'name': 'Warranty',
            'type': 'service',
            'website_published': True,
            'list_price': 20,
        })

    def test_onsite_payment_tour(self):
        # Make sure at least one onsite payment option exists.
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return

        self.env['delivery.carrier'].create({
            'delivery_type': 'onsite',
            'is_published': True,
            'website_published': True,
            'name': 'Example shipping On Site',
            'product_id': self.env.ref('website_sale_picking.onsite_delivery_product').id,
        })
        self.env.ref("website_sale_picking.payment_provider_onsite").state = 'enabled'
        self.env.ref("website_sale_picking.payment_provider_onsite").is_published = True

        self.start_tour('/shop', 'onsite_payment_tour')

    def test_onsite_payment_fiscal_change_tour(self):
        # Setup fiscal position
        (
            tax_5,
            tax_10,
            tax_15,
        ) = self.env['account.tax'].create([
            {
                'name': '5% Tax',
                'amount_type': 'percent',
                'amount': 5,
                'price_include': False,
                'include_base_amount': False,
                'type_tax_use': 'sale',
            },
            {
                'name': '10% Tax',
                'amount_type': 'percent',
                'amount': 10,
                'price_include': False,
                'include_base_amount': False,
                'type_tax_use': 'sale',
            },
            {
                'name': '15% Tax',
                'amount_type': 'percent',
                'amount': 15,
                'price_include': False,
                'include_base_amount': False,
                'type_tax_use': 'sale',
            },
        ])
        warehouse_fiscal_country = self.env['res.country'].create({
            'name': "Dummy Country",
            'code': 'DC',
        })
        # wsTourUtils.fillAdressForm() selects first country as address country
        client_fiscal_country = self.env['res.country'].search([('code', '=', 'AF')])

        self.env['product.product'].create({
            'name': 'Super Product',
            'list_price': 100.0,
            'type': 'consu',
            'website_published': True,
            'taxes_id': [Command.link(tax_15.id)]
        })

        self.env['account.fiscal.position'].create([
            {
                'name': 'Super Fiscal Position',
                'auto_apply': True,
                'country_id': warehouse_fiscal_country.id,
                'tax_ids': [
                    Command.create({
                        'tax_src_id': tax_15.id,
                        'tax_dest_id': tax_5.id,
                    })
                ]
            },
            {
                'name': 'Super Fiscal Position',
                'auto_apply': True,
                'country_id': client_fiscal_country.id,
                'tax_ids': [
                    Command.create({
                        'tax_src_id': tax_15.id,
                        'tax_dest_id': tax_10.id,
                    })
                ]
            },
        ])
        self.env.user.company_id.partner_id.country_id = warehouse_fiscal_country
        # Setup onsite picking with fiscal position different than user
        warehouse = self.env['stock.warehouse'].create({
            'name': "Warehouse",
            'partner_id': self.env.user.company_id.partner_id.id,
            'code': "WH01"
        })
        self.env['delivery.carrier'].create({
            'delivery_type': 'onsite',
            'is_published': True,
            'website_published': True,
            'name': 'Example shipping On Site',
            'product_id': self.env.ref('website_sale_picking.onsite_delivery_product').id,
            'warehouse_id': warehouse.id,
        })
        self.env.ref("website_sale_picking.payment_provider_onsite").state = 'enabled'
        self.env.ref("website_sale_picking.payment_provider_onsite").is_published = True
        self.start_tour('/shop', 'onsite_payment_fiscal_change_tour')
