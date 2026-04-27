# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from contextlib import contextmanager
from unittest.mock import patch

import requests

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@contextmanager
def _mock_envia_call():
    def _mock_request(*args, **kwargs):
        method = kwargs.get('method') or args[1]
        url = kwargs.get('url') or args[2]
        responses = {
            'GET': {
                'available-service': {
                    'data': [
                        {'carrier_id': 103, 'carrier_name': 'ups', 'id': 240, 'name': 'saver', 'description': 'UPS Express Saver', 'international': False},
                        {'carrier_id': 109, 'carrier_name': 'shippify', 'id': 255, 'name': 'express', 'description': 'Shippify Express', 'international': False},
                        {'carrier_id': 109, 'carrier_name': 'shippify', 'id': 256, 'name': 'slots', 'description': 'Shippify Slots', 'international': True},
                        {'carrier_id': 113, 'carrier_name': 'Jadlog', 'id': 265, 'name': 'expresso', 'description': 'Expresso', 'international': False},
                    ]
                },
                'additional-services': {
                    'data': [
                        {"name": "insurance", "description": "Insurance", "childs": [{"id": 14, "name": "insurance", "description": "Description", "json_structure": ""}]},
                        {"name": "liftgate_delivery", "description": "Liftgate Delivery", "childs": [{"id": 60, "name": "liftgate_delivery", "description": "Description", "json_structure": ""}]},
                        {"name": "lifgate_pickup", "description": "Lifgate Pickup", "childs": [{"id": 63, "name": "liftgate_pickup", "description": "Description", "json_structure": ""}]},
                        {"name": "pickup_residential", "description": "Pickup Residential", "childs": [{"id": 62, "name": "pickup_residential_zone", "description": "Pickup Residential Zone", "json_structure": ""}]},
                        {"name": "delivery_residential", "description": "Delivery Residential", "childs": [{"id": 61, "name": "delivery_residential_zone", "description": "Delivery Residential Zone", "json_structure": ""}]}
                    ]
                },
                'generic-form': [
                        {'fieldId': 'address1', 'fieldName': 'street', 'rules': {'required': True, 'validationType': 'street'}},
                        {'fieldId': 'address2', 'fieldName': 'number', 'rules': {'required': False, 'validationType': 'value'}},
                        {'fieldId': 'postalCode', 'fieldName': 'postal_code', 'rules': {'required': True, 'max': '20', 'validationType': 'value'}},
                        {'fieldId': 'city', 'fieldName': 'city', 'rules': {'required': True, 'max': '50', 'validationType': 'value'}},
                        {'fieldId': 'city_select', 'fieldName': 'city_select', 'rules': {'required': False, 'max': '50'}},
                        {'fieldId': 'state', 'fieldName': 'state', 'rules': {'required': True, 'min': '2', 'max': '3', 'validationType': 'select'}},
                        {'fieldId': 'reference', 'fieldName': 'reference', 'rules': {'required': False, 'max': '50'}}
                    ],
                'uploads/ups': ['WyJtb2NrTGFiZWw9PT09Il0=']
            },
            'POST': {
                'ship/rate': {
                    'meta': 'rate',
                    'data': [
                        {'carrier': 'ups', 'carrierDescription': 'UPS', 'carrierId': 103, 'serviceId': 240, 'quantity': 1, 'basePrice': 4.60, 'totalPrice': 4.60}
                    ]
                },
                'ship/generate': {
                    'meta': 'generate',
                    'data': [
                        {
                            'carrier': 'ups',
                            'service': 'saver',
                            'shipmentId': 1890000,
                            'trackingNumber': '1Z48746Q48746',
                            'trackUrl': 'https://test.envia.com/rastreo?label=1Z48746Q48746&cntry_code=us',
                            'label': 'https://s3.us-east-2.amazonaws.com/envia-staging/uploads/ups/1Z48746Q487462219663ea5a6a7da1.png',
                            'additionalFiles': [],
                            'totalPrice': 5.20,
                            'currency': 'USD'
                        }
                    ]
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
class TestDeliveryEnvia(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.your_company = cls.env.ref("base.main_partner")
        cls.your_company.write({
            'name': 'Odoo BR',
            'country_id': cls.env.ref('base.br').id,
            'street': 'Praça Mauá 1',
            'street2': 'Curitaba',
            'state_id': cls.env.ref('base.state_br_rj').id,
            'city': 'Rio de Janeiro',
            'zip': '20081-240',
            'phone': '+55 11 96123-4567',
        })
        cls.br_partner = cls.env['res.partner'].create({
            'name': 'Odoo BR Partner',
            'country_id': cls.env.ref('base.br').id,
            'street': 'Av. Presidente Vargas 592',
            'street2': 'Curitaba',
            'state_id': cls.env.ref('base.state_br_rj').id,
            'city': 'Rio de Janeiro',
            'zip': '30071-001',
            'phone': '+55 11 96123-4567',
        })
        # partner in us (azure)
        cls.us_partner = cls.env['res.partner'].create({
            'name': 'Azure Interior',
            'is_company': True,
            'street': '4557 De Silva St',
            'city': 'Fremont',
            'country_id': cls.env.ref('base.us').id,
            'zip': '94538',
            'state_id': cls.env.ref('base.state_us_5').id,
            'email': 'azure.Interior24@example.com',
            'phone': '(870)-931-0505',
        })


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

        cls.envia = cls.env.ref('delivery_envia.delivery_carrier_envia')

        cls.envia.write({
            'envia_production_api_key': 'mock_key',
            'envia_sandbox_api_key': 'mock_key',
            'envia_service_code': 'saver',
            'envia_carrier_code': 'ups'
        })

    def test_rate_order(self):
        """ Set up a sale order for an BR client and ensure that the rate is computed properly. """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.br_partner.id,
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
            'carrier_id': self.envia.id,
            'order_id': sale_order.id
        })

        with _mock_envia_call():
            choose_delivery_carrier.update_price()
            self.assertEqual(choose_delivery_carrier.delivery_price, 4.60)

    def test_rate_order_without_address(self):
        """ Set up a sale order without address and ensure that the rate computation fails. """
        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@example.com',
            'phone': '(870)-931-0505',
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id
                })
            ]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.envia.id,
            'order_id': sale_order.id
        })

        with _mock_envia_call():
            with self.assertRaises(ValidationError):
                choose_delivery_carrier.update_price()

    def test_shipping_order(self):
        """ Ensure that the shipping of an order works properly. """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.br_partner.id,
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
            'carrier_id': self.envia.id,
            'order_id': sale_order.id
        })
        with _mock_envia_call():
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
            self.assertEqual(picking.carrier_tracking_ref, "1Z48746Q48746", "The Envia Parcel Reference is not correct.")

            # Check that we the PDF is there with the correct title.
            pdf = picking.message_ids.attachment_ids.filtered(lambda m: m.description == 'LabelShipping-envia-1Z48746Q48746.PDF')
            self.assertNotEqual(pdf, self.env['ir.attachment'], "The label should be present as a pdf attachment.")
