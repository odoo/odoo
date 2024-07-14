# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.delivery_easypost.tests.common import EasypostTestCommon
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestDeliveryEasypostTour(HttpCase, EasypostTestCommon):
    def setUp(self):
        with self.patch_easypost_requests():
            super().setUp()

    def _get_client_action_url(self, delivery_carrier_id):
        action = self.env['ir.actions.actions']._for_xml_id('delivery.action_delivery_carrier_form')
        return '/web#action=%s&id=%s&view_type=form' % (action['id'], delivery_carrier_id)

    def test_carrier_type_selection_field(self):
        product = self.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
        })

        easypost_carrier = self.env['delivery.carrier'].create({
            'name': 'EASYPOST Test',
            'delivery_type': 'easypost',
            # API keys are not required, the response is mocked
            'easypost_test_api_key': 'test',
            'easypost_production_api_key': 'test',
            'product_id': product.id,
        })

        url = self._get_client_action_url(easypost_carrier.id)

        with self.patch_easypost_requests():
            self.start_tour(url, 'test_carrier_type_selection_field', login='admin', timeout=180)
