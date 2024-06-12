# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo.tests

from odoo.addons.website_sale.controllers.delivery import WebsiteSaleDelivery


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        transfer_provider = cls.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        # Avoid Shipping/Billing address page
        cls.env.ref('base.partner_admin').write({
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_39').id,
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        })

        cls.env['product.product'].create({
            'name': 'Office Chair Black TEST',
            'list_price': 12.50,
        })
        cls.env.ref("delivery.free_delivery_carrier").write({
            'name': 'Delivery Now Free Over 10',
            'fixed_price': 2,
            'free_over': True,
            'amount': 10,
        })
        cls.product_delivery_poste = cls.env['product.product'].create({
            'name': 'The Poste',
            'type': 'service',
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
            'sale_ok': False,
            'purchase_ok': False,
            'list_price': 20.0,
        })
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'The Poste',
            'sequence': 9999, # ensure last to load price async
            'fixed_price': 20.0,
            'delivery_type': 'base_on_rule',
            'product_id': cls.product_delivery_poste.id,
            'website_published': True,
        })

    def test_01_free_delivery_when_exceed_threshold(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")
        self.env['delivery.price.rule'].create([{
            'carrier_id': self.carrier.id,
            'max_value': 5,
            'list_base_price': 20,
        }, {
            'carrier_id': self.carrier.id,
            'operator': '>=',
            'max_value': 5,
            'list_base_price': 50,
        }, {
            'carrier_id': self.carrier.id,
            'operator': '>=',
            'max_value': 300,
            'variable': 'price',
            'list_base_price': 0,
        }])

        self.start_tour("/", 'check_free_delivery', login="admin")

    def test_pay_button_disabled_when_carrier_has_error(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")
        Monetary = self.env['ir.qweb.field.monetary']
        usd_currency = self.env.ref('base.USD')
        with patch.object(WebsiteSaleDelivery, '_get_rate',
                          lambda controller, *args, **kwargs: {
                              'success': False,
                              'price': 0.0,
                              'error_message': 'this is a test error message',
                              'warning_message': False
                          }), \
             patch.object(WebsiteSaleDelivery, '_update_website_sale_delivery_return',
                          lambda contoller, *args, **kwargs: {
                              'status': False,
                              'error_message': 'this is a test error message',
                              'carrier_id': self.carrier.id,
                              'is_free_delivery': True,
                              'new_amount_delivery': Monetary.value_to_html(0.0, {'display_currency': usd_currency}),
                          }):
            self.start_tour("/", 'check_errored_delivery', login="admin")
