# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from contextlib import contextmanager
from unittest.mock import patch

import requests

from odoo import Command
from odoo.tests import TransactionCase, tagged


@contextmanager
def _mock_starshipit_call():
    def _mock_request(*args, **kwargs):
        method = kwargs.get('method') or args[0]
        url = kwargs.get('url') or args[1]
        data = kwargs.get('json') or {}
        responses = {
            'GET': {
                '/shipment/clone': {
                    'success': True,
                    'order': {'order_id': 'CP0123457', 'order_number': data.get('orders', [{}])[0].get('order_number')},
                },
                'orders': {
                    'success': True,
                    'order': {'order_id': 'CP0123456', 'manifested': False, 'total_shipping_price': 4.20}
                }
            },
            'POST': {
                'deliveryservices': {
                    'success': True,
                    'services': [{'carrier': 'CourierPost', 'carrier_name': 'Courier Post', 'service_name': 'Courier Post Island', 'service_code': 'CP01IL', 'total_price': 4.20}]
                },
                'rates': {
                    'success': True,
                    'rates': [
                        {'service_name': 'Courier Post Island', 'service_code': 'CP01IL', 'total_price': 4.20},
                        {'service_name': 'Courier Post Inland', 'service_code': 'CP02IL', 'total_price': 6.90},
                    ]
                },
                # For simplicity, we only set the two id's used by the backend.
                'orders/import': {
                    'success': True,
                    'orders': [{'order_id': 'CP0123456', 'order_number': data.get('orders', [{}])[0].get('order_number')}],
                },
                'orders/shipment': {
                    'success': True,
                    'tracking_numbers': ['123tracking'],
                    'labels': ['WW91J3JlIGEgY3VyaW91cyBvbmUgYXJlbid0IHlvdQ=='],
                },
                'archive': {
                    'success': True,
                },
            }
        }

        for endpoint, content in responses[method].items():
            if endpoint in url:
                response = requests.Response()
                response._content = json.dumps(content).encode()
                response.status_code = 200
                return response

        raise Exception('unhandled request url %s' % url)

    with patch.object(requests.Session, 'request', _mock_request):
        yield


@tagged('post_install', '-at_install')
class TestDeliveryStarShipIt(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.your_company = cls.env.ref("base.main_partner")
        cls.your_company.write({
            'name': 'Odoo SAU',
            'country_id': cls.env.ref('base.au').id,
            'street': '25 Walters Street',
            'street2': False,
            'state_id': cls.env.ref('base.state_au_7').id,
            'city': 'Taminick',
            'zip': 3675,
            'phone': '0353483783',
        })
        cls.au_partner = cls.env.ref('base.res_partner_2')
        cls.au_partner.write({
            'country_id': cls.env.ref('base.au').id,
            'street': '26 Acheron Road',
            'street2': False,
            'state_id': cls.env.ref('base.state_au_7').id,
            'city': 'Hazelwood North',
            'zip': 3840,
            'phone': '0353229781',
        })
        # partner in us (azure)
        cls.us_partner = cls.env.ref('base.res_partner_12')

        cls.product_to_ship1 = cls.env["product.product"].create({
            'name': 'Door with Legs',
            'type': 'consu',
            'weight': 10.0
        })

        cls.product_to_ship2 = cls.env["product.product"].create({
            'name': 'Door with Arms',
            'type': 'consu',
            'weight': 15.0
        })

        shipping_product = cls.env['product.product'].create({
            'name': 'StarShipIt Delivery',
            'type': 'service'
        })

        cls.starshipit = cls.env['delivery.carrier'].create({
            'delivery_type': 'starshipit',
            'product_id': shipping_product.id,
            'starshipit_api_key': 'mock_key',
            'starshipit_subscription_key': 'mock_key',
            'name': 'StarShipIt',
            'starshipit_service_code': 'CP01IL',
            'starshipit_carrier_code': 'CourierPost',
        })

        cls.starshipit_second = cls.env['delivery.carrier'].create({
            'delivery_type': 'starshipit',
            'product_id': shipping_product.id,
            'starshipit_api_key': 'mock_key',
            'starshipit_subscription_key': 'mock_key',
            'name': 'StarShipIt Second',
            'starshipit_service_code': 'CP02IL',
            'starshipit_carrier_code': 'CourierPost',
        })

    def test_rate_order(self):
        """ Set up a sale order for an AU client and ensure that the rate is computed properly. """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.au_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id
                }),
                Command.create({
                    'product_id': self.product_to_ship2.id
                })
            ]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.starshipit.id,
            'order_id': sale_order.id
        })
        with _mock_starshipit_call():
            choose_delivery_carrier.update_price()
            self.assertEqual(choose_delivery_carrier.delivery_price, 4.20)

    def test_shipping_order(self):
        """ Ensure that the shipping of an order works properly. """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.au_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id
                }),
                Command.create({
                    'product_id': self.product_to_ship2.id
                })
            ]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.starshipit.id,
            'order_id': sale_order.id
        })
        with _mock_starshipit_call():
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for shipment.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "The carrier is not the same on Picking and on SO.")
            picking.action_assign()
            picking.move_ids.picked = True
            self.assertGreater(picking.weight, 0.0, "The picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.starshipit_parcel_reference, False, "The StarShipIt Parcel Reference is not set")

            # Check that we the PDF is there and contains the "label"
            pdf = picking.message_ids.attachment_ids.filtered(lambda m: m.datas == b'WW91J3JlIGEgY3VyaW91cyBvbmUgYXJlbid0IHlvdQ==')
            self.assertNotEqual(pdf, self.env['ir.attachment'], "The label should be present as a pdf attachment.")

    def test_generate_return(self):

        sale_order = self.env['sale.order'].create({
            'partner_id': self.au_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id
                }),
                Command.create({
                    'product_id': self.product_to_ship2.id
                })
            ]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.starshipit.id,
            'order_id': sale_order.id
        })
        with _mock_starshipit_call():
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for shipment.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "The carrier is not the same on Picking and on SO.")
            picking.action_assign()
            picking.move_ids.picked = True
            self.assertGreater(picking.weight, 0.0, "The picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.starshipit_parcel_reference, False, "The StarShipIt Parcel Reference is not set")
            # The parcel has been processed, but we wish to return it
            picking.carrier_id.starshipit_get_return_label(picking)
            self.assertIsNot(picking.starshipit_return_parcel_reference, False, "The StarShipIt Return Parcel Reference is not set")
            pdf = picking.message_ids.attachment_ids.filtered(lambda m: m.datas == b'WW91J3JlIGEgY3VyaW91cyBvbmUgYXJlbid0IHlvdQ==')
            self.assertEqual(len(pdf), 2, "There should be two label, one for the shipping and one for the return.")
