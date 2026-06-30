# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import lxml.html

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.website.tests.common import HttpCaseWithWebsiteUser

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestSaleProcess(HttpCaseWithUserDemo, WebsiteSaleCommon, HttpCaseWithWebsiteUser):

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
        cls.partner_website_user.write(cls.dummy_partner_address_values)

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
        self.partner_demo.write(self.dummy_partner_address_values)
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
        # Data for google_analytics_view_item
        attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 10,
            'display_type': 'color',
            'value_ids': [
                Command.create({
                    'name': 'Red',
                }),
                Command.create({
                    'name': 'Pink',
                }),
            ]
        })
        self.env['product.template'].create({
            'name': 'Colored T-Shirt',
            'standard_price': 500,
            'list_price': 750,
            'type': 'consu',
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': attribute.value_ids,
                })
            ]
        })
        self.env['website'].browse(1).write({'google_analytics_key': 'G-XXXXXXXXXXX'})
        self.start_tour("/shop", 'google_analytics_view_item')
        # Data for google_analytics_add_to_cart
        self.env['product.template'].create({
            'name': 'Basic Shirt',
            'standard_price': 500,
            'type': 'consu',
            'website_published': True
        })
        self.start_tour("/shop", 'google_analytics_add_to_cart')

    def test_06_public_user_shop_repair(self):
        """ Public user purchasing repair service products in website shop. """
        if self.env['ir.module.module']._get('repair').state != 'installed':
            self.skipTest("Repair is not installed")

        self.env['product.template'].create({
            'name': 'Test Repair Service',
            'type': 'service',
            'service_tracking': 'repair',
            'sale_ok': True,
            'is_published': True,
        })
        self.start_tour("/", 'shop_repair_product', login=None)

    def test_checkout_with_rewrite(self):
        # check that checkout page can be open with step rewritten
        self.env['website.rewrite'].create({
            'name': 'Test Address Rename',
            'redirect_type': '308',
            'url_from': '/shop/address',
            'url_to': '/test/address',
        })
        self.env['website.rewrite'].create({
            'name': 'Test Checkout Rename',
            'redirect_type': '308',
            'url_from': '/shop/checkout',
            'url_to': '/test/checkout',
        })
        self._create_so(partner_id=self.user_demo.partner_id.id)
        self.authenticate('demo', 'demo')
        response = self.url_open('/shop/address')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.url[-13:], '/test/address')

        # check that navigation (next and previous checkout steps) are correct
        allowed_steps_domain = self.website._get_allowed_steps_domain()
        checkout_step = self.env.ref('website_sale.checkout_step_delivery')
        previous_step = checkout_step._get_previous_checkout_step(allowed_steps_domain)
        next_step = checkout_step._get_next_checkout_step(allowed_steps_domain)
        root = lxml.html.fromstring(response.content)
        self.assertEqual(len(root.xpath(f'//a[@href="{previous_step.step_href}"]//span[text()="{previous_step.back_button_label}"]')), 2)
        self.assertEqual(len(root.xpath(f'//a[@name="website_sale_main_button"][not(@href)]//span[text()="{next_step.main_button_label}"]')), 2)

    def test_update_same_address_billing_shipping_edit(self):
        ''' Phone field should be required when updating an adress for billing and shipping '''
        self.env['product.product'].create({
            'name': 'Office Chair Black TEST',
            'list_price': 12.50,
            'is_published': True,
        })
        self.start_tour("/shop", 'update_billing_shipping_address', login="website_user")
