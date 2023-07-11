# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.addons.website.tools import MockRequest
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestWebsiteSaleDeliveryController(PaymentCommon):
    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.Controller = WebsiteSaleDelivery()

    # test that changing the carrier while there is a pending transaction raises an error
    def test_controller_change_carrier_when_transaction(self):
        with MockRequest(self.env, website=self.website):
            order = self.website.sale_get_order(force_create=True)
            order.transaction_ids = self._create_transaction(flow='redirect', state='pending')
            with self.assertRaises(UserError):
                with patch(
                    'odoo.addons.website_sale.models.website.Website.sale_get_order',
                    return_value=order,
                ):  # Patch to retrieve the order even if it is linked to a pending transaction.
                    self.Controller.update_eshop_carrier(carrier_id=1)

    # test that changing the carrier while there is a draft transaction doesn't raise an error
    def test_controller_change_carrier_when_draft_transaction(self):
        with MockRequest(self.env, website=self.website):
            order = self.website.sale_get_order(force_create=True)
            order.transaction_ids = self._create_transaction(flow='redirect', state='draft')
            self.Controller.update_eshop_carrier(carrier_id=1)

    def test_address_states(self):
        US = self.env.ref('base.us')
        MX = self.env.ref('base.mx')

        # Set all carriers to mexico
        self.env['delivery.carrier'].sudo().search([('website_published', '=', True)]).country_ids = [(6, 0, [MX.id])]

        # Create a new carrier to only one state in mexico
        self.env['delivery.carrier'].create({
                'name': "One_state",
                'product_id': self.env['product.product'].create({'name': "delivery product"}).id,
                'website_published': True,
                'country_ids': [(6, 0, [MX.id])],
                'state_ids': [(6, 0, [MX.state_ids.ids[0]])]
        })

        country_info = self.Controller.country_infos(country=MX, mode="shipping")
        self.assertEqual(len(country_info['states']), len(MX.state_ids))

        country_info = self.Controller.country_infos(country=US, mode="shipping")
        self.assertEqual(len(country_info['states']), 0)
