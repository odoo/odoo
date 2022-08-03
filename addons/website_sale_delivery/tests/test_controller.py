# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
                self.Controller.update_eshop_carrier(carrier_id=1)
