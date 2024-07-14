import json
from contextlib import contextmanager
from unittest.mock import patch
import requests
from odoo.tests.common import TransactionCase, tagged


@contextmanager
def _mock_request_call():
    def _mock_request(*args, **kwargs):
        url = kwargs.get('url')
        if 'shipments' in url:
            url = url.split('/shipments')[1]
        responses = {
            'token': {'access_token': 'mock_token'},
            'rating': {'RateResponse': {
                'Response': {
                    "Alert": {"Code": "string", "Description": "string"},
                },
                'RatedShipment': {'TotalCharges': {'MonetaryValue': '5.5', 'CurrencyCode': 'USD'}}}},
            'ship': {'ShipmentResponse': {'ShipmentResults': {
                'ShipmentCharges': {'TotalCharges': {'MonetaryValue': '5.5', 'CurrencyCode': 'USD'}},
                'ShipmentIdentificationNumber': '123',
                'PackageResults': {'TrackingNumber': '123', 'ShippingLabel': {'GraphicImage': 'some_imag'}}
                }}},
            'cancel': {'VoidShipmentResponse': {'SummaryResult': {'Status': {}}}},
        }

        for endpoint, content in responses.items():
            if endpoint in url:
                response = requests.Response()
                response._content = json.dumps(content).encode()
                response.status_code = 200
                return response

        raise Exception('unhandled request url %s' % url)

    with patch.object(requests.Session, 'request', _mock_request):
        yield


@tagged('post_install', '-at_install')
class TestDeliveryUPS(TransactionCase):

    def setUp(self):
        super().setUp()

        self.env.company.partner_id.write({
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_5').id,
            'city': 'Los Angelos',
            'street': 'My street',
            'phone': '1234567890',
            'zip': '1234',
        })

        shipping_product = self.env['product.product'].create({
            'name': 'UPS Delivery',
            'type': 'service',
        })

        self.ups_delivery = self.env['delivery.carrier'].create({
            'name': 'ups',
            'delivery_type': 'ups_rest',
            'ups_shipper_number': 'mock',
            'ups_client_id': 'mock',
            'ups_client_secret': 'mock',
            'ups_default_service_type': '11',
            'product_id': shipping_product.id,
            'ups_label_file_type': 'ZPL',
            'ups_default_packaging_id': self.env.ref('delivery_ups_rest.ups_packaging_25').id,  # 10 kg box
        })

        self.product = self.env['product.product'].create({
            'name': 'fancy box',
            'type': 'consu',
            'weight': 10.0,
        })

        self.partner = self.env['res.partner'].create({
            'name': 'Cool Customer',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_5').id,
            'street': 'My street',
            'city': 'Los Angelos',
            'phone': '1234567890',
            'zip': '1234',
        })

    def test_ups_basic_flow(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': "Fancy box",
                'product_uom_qty': 1.0,
                'price_unit': 20,
            })]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.ups_delivery.id,
            'order_id': sale_order.id
        })
        with _mock_request_call():
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            self.assertEqual(choose_delivery_carrier.display_price, 5.5)
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for shipment.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")
            picking.action_assign()
            picking.move_line_ids[0].quantity = 1.0
            self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")
            picking._action_done()
            self.assertEqual(picking.carrier_tracking_ref, '123', 'Tracking ref should be set from mock response')
            self.assertEqual(picking.carrier_price, 5.5, 'Price should be set from mock response')
            picking.cancel_shipment()
            self.assertEqual(picking.carrier_tracking_ref, False, 'Shipment cancel failed')
