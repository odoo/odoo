# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_collect.controllers.delivery import InStoreDelivery
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestInStoreDeliveryController(PaymentHttpCommon, ClickAndCollectCommon):
    def setUp(self):
        super().setUp()
        self.InStoreController = InStoreDelivery()

    def test_order_not_created_on_fetching_pickup_location_with_empty_cart(self):
        count_so_before = self.env['sale.order'].search_count([])
        url = self._build_url('/website_sale/get_pickup_locations')
        with patch(
            'odoo.addons.website_sale_collect.models.sale_order.SaleOrder._get_pickup_locations',
            return_value={}
        ):
            self.make_jsonrpc_request(url, {'product_id': 1})
        count_so_after = self.env['sale.order'].search_count([])
        self.assertEqual(count_so_after, count_so_before)

    def test_limit_pickup_locations_to_website_company(self):
        """Make sure that the warehouses proposed as a pickup location for an order
        have the same company as the order, to prevent company inconsistencies
        """
        other_company = self.env['res.company'].create({'name': 'Other Company'})
        self.in_store_dm.warehouse_ids += self._create_warehouse(company_id=other_company.id)
        self.assertEqual(len(self.in_store_dm.warehouse_ids), 2)

        url = self._build_url('/website_sale/get_pickup_locations')
        result = self.make_jsonrpc_request(url, {'product_id': 1})['pickup_locations']
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.warehouse.id)

        so = self._create_in_store_delivery_order()
        with MockRequest(self.env, website=self.website, sale_order_id=so.id):
            result = self.InStoreController.website_sale_get_pickup_locations(product_id=1)['pickup_locations']
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['id'], self.warehouse.id)
