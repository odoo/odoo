# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

from odoo import Command
from odoo.addons.base.tests.common import HttpCase


class TestWebsiteSaleTaxCloud(HttpCase):

    def setUp(self):
        super().setUp()
        self.env.company.country_id = self.env.ref('base.us')
        self.env['account.tax.group'].create(
            {'name': 'Test Tax Group', 'company_id': self.env.company.id}
        )

        self.acquirer = self.env.ref('payment.payment_provider_transfer')
        self.payment_method_id = self.env.ref('payment.payment_method_unknown').id

        self.fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'BurgerLand',
            'is_taxcloud': True,
        })

        self.partner = self.env['res.partner'].create({
            'name': 'Customer'
        })

        self.product = self.env['product.product'].create({
            'name': 'A',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': False,
            'website_published': True,
        })

    def _verify_address(self, *args):
        return {
            'apiLoginID': '',
            'apiKey': '',
            'Address1': '',
            'Address2': '',
            'City': '',
            "State": '',
            "Zip5": '',
            "Zip4": '',
        }

    def _get_all_taxes_values(self):
        return {'values': {0: 10}}

    def test_recompute_taxes_before_payment(self):
        """
        Make sure that taxes are recomputed before payment
        """
        self.product.type = 'service'
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'fiscal_position_id': self.fiscal_position.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                })
            ]
        })
        sale_order.access_token = "token"

        with \
                patch('odoo.addons.account_taxcloud.models.taxcloud_request.TaxCloudRequest.verify_address', self._verify_address),\
                patch('odoo.addons.account_taxcloud.models.taxcloud_request.TaxCloudRequest.get_all_taxes_values', self._get_all_taxes_values),\
                patch.object(type(sale_order), '_get_TaxCloudRequest', return_value=sale_order._get_TaxCloudRequest("id", "api_key")):

            self.assertFalse(sale_order.order_line[0].tax_id)

            response = self.url_open(
                f'/shop/payment/transaction/{sale_order.id}',
                headers={'Content-Type': 'application/json'},
                data=json.dumps({
                    'params': {
                        'access_token': sale_order.access_token,
                        'amount': 110,
                        'provider_id': self.acquirer.id,
                        'payment_method_id': self.payment_method_id,
                        'token_id': False,
                        'tokenization_requested': True,
                        'flow': 'direct',
                        'landing_route': 'Test'
                    }
                })
            )
            response.raise_for_status()
            self.assertEqual(list(response.json().keys()), ["jsonrpc", "id", "result"], "should be a valid jsonrpc response")

            sale_order.order_line[0].invalidate_recordset()
            self.assertTrue(sale_order.order_line[0].tax_id)
