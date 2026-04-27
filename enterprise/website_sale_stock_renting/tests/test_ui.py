# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import freezegun

from odoo import http, Command
from odoo.tests import HttpCase, tagged
from odoo.addons.website_sale_renting.tests.common import TestWebsiteSaleRentingCommon
from datetime import datetime

@tagged('-at_install', 'post_install')
class TestUi(HttpCase, TestWebsiteSaleRentingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.user_admin').write({
            'company_id': cls.env.company.id,
            'company_ids': [(4, cls.env.company.id)],
            'name': 'Mitchell Admin',
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_39').id,
        })
        cls.env.ref('base.user_admin').sudo().partner_id.company_id = cls.env.company
        cls.env.ref('website.default_website').company_id = cls.env.company
        cls.computer.is_storable = True
        cls.computer.allow_out_of_stock_order = False
        cls.computer.show_availability = True

        quants = cls.env['stock.quant'].create({
            'product_id': cls.computer.id,
            'inventory_quantity': 5.0,
            'location_id': cls.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quants.action_apply_inventory()

    def test_website_sale_stock_renting_ui(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.sudo().write({
            'state': 'enabled',
            'is_published': True,
            'company_id': self.env.company.id,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.start_tour("/odoo", 'shop_buy_rental_stock_product', login='admin')

    def test_website_availability_update(self):
        product_template = self.env['product.template'].create({
            'name': 'Test Product with Variants',
            'type': 'consu',
            'rent_ok': True,
            'is_published': True,
            'website_published': True,
            'show_availability': True,
            'allow_out_of_stock_order': False,
            'is_storable': True,
        })

        attribute = self.env['product.attribute'].create({
            'name': 'Size',
        })

        attribute_value_small = self.env['product.attribute.value'].create({
            'name': 'Small',
            'attribute_id': attribute.id,
        })
        attribute_value_large = self.env['product.attribute.value'].create({
            'name': 'Large',
            'attribute_id': attribute.id,
        })

        product_template.attribute_line_ids = [(Command.create({
            'attribute_id': attribute.id,
            'value_ids': [Command.set([attribute_value_small.id, attribute_value_large.id])],
        }))]

        recurrence = self.env['sale.temporal.recurrence'].sudo().create({'duration': 1, 'unit': 'hour'})
        self.env['product.pricing'].create([
            {
                'recurrence_id': recurrence.id,
                'price': 1000,
                'product_template_id': product_template.id,
                'product_variant_ids': product_template.product_variant_ids,
            },
        ])

        # Get the product variants
        variant_small = product_template.product_variant_ids.filtered(lambda v: attribute_value_small in v.product_template_attribute_value_ids.product_attribute_value_id)
        variant_large = product_template.product_variant_ids.filtered(lambda v: attribute_value_large in v.product_template_attribute_value_ids.product_attribute_value_id)

        self.env['stock.quant'].create({
            'product_id': variant_small.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 1,
        })

        self.env['stock.quant'].create({
            'product_id': variant_large.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 0,
        })

        self.start_tour("/web", 'website_availability_update', login='admin')

    @freezegun.freeze_time('2024-12-18 12:00:00')
    def test_website_availability_while_continuing_selling(self):
        self.computer.allow_out_of_stock_order = True
        rental = self.env['sale.order'].with_context(in_rental_app=True).create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
            'rental_start_date': datetime(2024, 12, 18, 0, 0),
            'rental_return_date': datetime(2024, 12, 21, 0, 0),
            'warehouse_id': self.env.user._get_default_warehouse_id().id,
            'order_line': [
                Command.create({
                    'product_id': self.computer.id,
                    'product_uom_qty': 3,
                }),
            ]
        })

        rental.action_confirm()

        self.start_tour("/web", 'test_website_availability_while_continuing_selling', login='admin')

    @freezegun.freeze_time('2020-01-01')
    def test_visitor_browse_rental_products(self):
        """
        This tests validate that a visitor can actually browse
        on /shop for rental product with the datepicker and is not met with access error
        because he doesn't read access to warehouse (to check for quantities)
        and the sale.order.lines to check availability of the rental product.
        """
        self.env['product.product'].create({
            'is_storable': True,
            'name': 'Test product',
            'rent_ok': True,
            'allow_out_of_stock_order': False,
            'is_published': True,
            'qty_available': 1,
        })
        self.authenticate(None, None)
        response = self.url_open('/shop', {
            'start_date': '2020-01-02 00:00:00',
            'end_date': '2020-01-03 00:00:00',
            'csrf_token': http.Request.csrf_token(self),
        })
        self.assertNotEqual(response.status_code, 403,
                            "An access error was raised, because a public visitor doesn't have access "
                            "to the warehouse and sale order line read access.")
