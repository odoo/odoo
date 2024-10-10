# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_sale.tests.test_sale_process import TestWebsiteSaleCheckoutAddress
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install')
class TestWebsiteSaleController(TestWebsiteSaleCheckoutAddress):
    def setUp(self):
        super().setUp()

    def test_carrier_update_on_shop_payment(self):
        """ Test that a correct carrier is set on SO on shop/payment when partner_shipping_id is
        changed. """

        # Unpublish all carriers.
        self.env['delivery.carrier'].search([]).website_published = False

        country_be = self.env.ref('base.be')
        country_fr = self.env.ref('base.fr')

        # Create a delivery product.
        self.product_delivery_poste = self.env['product.product'].create({
            'name': 'The Poste',
            'type': 'service',
            'categ_id': self.env.ref('delivery.product_category_deliveries').id,
            'sale_ok': False,
            'purchase_ok': False,
        })

        # Create a carrier which ships only to Belgium.
        carrier_be = self.env['delivery.carrier'].create([{
            'name': 'Fixed BE',
            'product_id': self.product_delivery_poste.id,
            'country_ids': [Command.set([country_be.id])],
            'website_published': True,
        }])

        # Create a carrier which ships only to France.
        carrier_fr = self.env['delivery.carrier'].create([{
            'name': 'Fixed FR',
            'product_id': self.product_delivery_poste.id,
            'country_ids': [Command.set([country_fr.id])],
            'website_published': True,
        }])

        # Create partner_shipping_id with BE country.
        p = self.env.user.partner_id
        so = self._create_so(p.id)
        so.partner_shipping_id = self.env['res.partner'].create({
            'name': 'a res.partner address',
            'email': 'email@email.email',
            'street': 'ooo',
            'city': 'ooo',
            'zip': '1200',
            'country_id': country_be.id,
            'parent_id': p.id,
            'type': 'delivery',
        })
        so.set_delivery_line(carrier_be, carrier_be.fixed_price)
        with MockRequest(self.env, website=self.website, sale_order_id=so.id):
            # Change the country of the partner_shipping_id.
            so.partner_shipping_id.country_id = country_fr
            WebsiteSaleDelivery().shop_payment()
            # Check that a carrier is updated.
            self.assertEqual(so.carrier_id, carrier_fr)
