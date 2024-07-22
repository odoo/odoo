# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.fields import Command
from odoo.tests import loaded_demo_data, tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestSaleProcess(HttpCaseWithUserDemo, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storage_box = cls.env['product.product'].create({
            'name': 'Storage Box',
            'standard_price': 70.0,
            'list_price': 79.0,
            'website_published': True,
        })
        cls.product_attribute_legs = cls.env['product.attribute'].create({
            'name': 'Legs',
            'sequence': 10,
            'value_ids': [
                Command.create({
                    'name': 'Steel',
                    'sequence': 1,
                }),
                Command.create({
                    'name': 'Aluminium',
                    'sequence': 2,
                }),
            ],
        })
        cls.conference_chair = cls.env['product.template'].create({
            'name': 'Conference Chair',
            'list_price': 16.50,
            'website_published': True,
            'accessory_product_ids': [Command.link(cls.storage_box.id)],
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': cls.product_attribute_legs.id,
                    'value_ids': [Command.set(cls.product_attribute_legs.value_ids.ids)],
                })
            ],
        })

        cls.chair_floor_protection = cls.env['product.template'].create({
            'name': 'Chair floor protection',
            'list_price': 12.0,
        })
        # Crappy hack: But otherwise the "Proceed To Checkout" modal button won't be displayed
        if 'optional_product_ids' in cls.env['product.template']:
            cls.conference_chair.optional_product_ids = [Command.set(cls.chair_floor_protection.ids)]

        cls.env['account.journal'].create({
            'name': 'Cash - Test',
            'type': 'cash',
            'code': 'CASH - Test',
        })

        # Avoid Shipping/Billing address page
        cls.env.ref('base.partner_admin').write(cls.dummy_partner_address_values)

        if cls.env['ir.module.module']._get('payment_custom').state == 'installed':
            transfer_provider = cls.env.ref('payment.payment_provider_transfer')
            transfer_provider.write({
                'state': 'enabled',
                'is_published': True,
            })
            transfer_provider._transfer_ensure_pending_msg_is_set()

    def test_01_admin_shop_tour(self):
        self.start_tour(self.env['website'].get_client_action_url('/shop'), 'test_01_admin_shop_tour', login='admin')

    def test_01_cart_update_check(self):
        self.start_tour('/', 'shop_update_cart', login='admin')

    def test_02_admin_checkout(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        self.start_tour("/", 'shop_buy_product', login="admin")

    def test_03_demo_checkout(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        self.start_tour("/", 'shop_buy_product', login="demo")

    def test_04_admin_website_sale_tour(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        self.env.company.country_id = self.country_us
        tax_group = self.env['account.tax.group'].create({'name': 'Tax 15%'})
        tax = self.env['account.tax'].create({
            'name': 'Tax 15%',
            'amount': 15,
            'type_tax_use': 'sale',
            'tax_group_id': tax_group.id
        })
        # storage box
        self.product_product_7 = self.env['product.product'].create({
            'name': 'Storage Box Test',
            'standard_price': 70.0,
            'list_price': 79.0,
            'website_published': True,
            'invoice_policy': 'delivery',
        })
        self.product_product_7.taxes_id = [tax.id]
        self.env['res.config.settings'].create({
            'auth_signup_uninvited': 'b2c',
            'show_line_subtotals_tax_selection': 'tax_excluded',
        }).execute()

        self.start_tour("/", 'website_sale_tour_1')
        self.start_tour(
            self.env['website'].get_client_action_url('/shop/cart'),
            'website_sale_tour_backend',
            login='admin'
        )
        self.start_tour("/", 'website_sale_tour_2', login="admin")

    def test_05_google_analytics_tracking(self):
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.env['website'].browse(1).write({'google_analytics_key': 'G-XXXXXXXXXXX'})
        self.start_tour("/shop", 'google_analytics_view_item')
        self.start_tour("/shop", 'google_analytics_add_to_cart')

    def test_update_same_address_billing_shipping_edit(self):
        ''' Phone field should be required when updating an adress for billing and shipping '''
        self.env['product.product'].create({
            'name': 'Office Chair Black TEST',
            'list_price': 12.50,
            'is_published': True,
        })
        self.start_tour("/shop", 'update_billing_shipping_address', login="admin")
