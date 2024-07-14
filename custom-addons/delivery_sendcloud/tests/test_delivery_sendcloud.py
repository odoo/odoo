import json
from contextlib import contextmanager
from unittest.mock import patch
import requests

from odoo.tests import TransactionCase, tagged
from odoo import Command

@contextmanager
def _mock_sendcloud_call(warehouse_id):
    def _mock_request(*args, **kwargs):
        method = kwargs.get('method') or args[0]
        url = kwargs.get('url') or args[1]
        responses = {
            'get': {
                'shipping-products': [
                    {
                        "name": "Test Product",
                        "carrier": "test",
                        "service_points_carrier": "test",
                        "available_functionalities": {
                            "last_mile": [
                                "service_point",
                                "home_delivery",
                            ],
                            "multicollo": [
                                True,
                            ],
                            "signature": [
                                True,
                            ],
                            "delivery_attempts": [
                                1,
                            ],
                            "delivery_deadline": [
                                "best_effort",
                            ],
                        },
                        "methods": [
                            {
                                "id": 1,
                                "name": "Test 0-10 Kg",
                                "functionalities": {},
                                "shipping_product_code": "test:product",
                                "properties": {
                                    "min_weight": 1,
                                    "max_weight": 10001,
                                    "max_dimensions": {
                                        "length": 100,
                                        "width": 50,
                                        "height": 80,
                                        "unit": "centimeter",
                                    }
                                },
                            },
                            {
                                "id": 2,
                                "name": "Test 10-20 Kg",
                                "functionalities": {},
                                "shipping_product_code": "test:product",
                                "properties": {
                                    "min_weight": 10001,
                                    "max_weight": 20001,
                                    "max_dimensions": {
                                        "length": 100,
                                        "width": 80,
                                        "height": 50,
                                        "unit": "centimeter",
                                    }
                                },
                            },
                            {
                                "id": 3,
                                "name": "Test 0-20 Kg with signature",
                                "functionalities": {
                                    "signature": True,
                                },
                                "shipping_product_code": "test:product",
                                "properties": {
                                    "min_weight": 1,
                                    "max_weight": 20001,
                                    "max_dimensions": {
                                        "length": 90,
                                        "width": 50,
                                        "height": 50,
                                        "unit": "centimeter",
                                    }
                                },
                            },
                        ],
                        "code": "test:product",
                        "weight_range": {
                            "min_weight": 1,
                            "max_weight": 20001,
                        },
                    }
                ],
                'shipping-price': {
                    1: [{
                        'price': '1.1',
                        'currency': 'USD'  # Usually, Sendcloud use EUR, but we here use USD to avoid currency conversion and ease the testing
                    }],
                    2: [{
                        'price': '2.2',
                        'currency': 'USD'
                    }],
                    3: [{
                        'price': '3.3',
                        'currency': 'USD'
                    }],
                },
                'addresses': {'sender_addresses': [{'contact_name': warehouse_id.name, 'id': 1}]},
                'label': 'mock',
            },
            'post': {
                'parcels': {
                    'parcels': [{
                        'tracking_number': '123',
                        'tracking_url': 'url',
                        'id': 1, 'weight': 10.0,
                        'shipment': {'id': 8},
                        'documents': [{'link': '/label', 'type': 'label'}],
                        'colli_uuid': '4dc5e2dc-e0be-4814-a6fd-fdf96dd4a9b6',
                    }],
                    'status': 'deleted'
                },
            }
        }
        for endpoint, content in responses[method].items():
            if endpoint in url:
                response = requests.Response()
                if endpoint == 'shipping-products' and 'weight' in kwargs.get('params', {}):
                    weight = kwargs['params']['weight']
                    for product in content:
                        product['methods'] = list(filter(lambda m: m['properties']['min_weight'] <= weight <= m['properties']['max_weight'], product['methods']))
                elif endpoint == 'shipping-price':
                    method_id = (kwargs.get('params') or args[3]).get('shipping_method_id')
                    content = content[method_id]

                response._content = json.dumps(content).encode()
                response.status_code = 200
                return response

        raise Exception('unhandled request url %s' % url)

    with patch.object(requests.Session, 'request', _mock_request):
        yield

@tagged('-standard', 'external')
class TestDeliverySendCloud(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.your_company = cls.env.ref("base.main_partner")
        cls.warehouse_id = cls.env['stock.warehouse'].search([('company_id', '=', cls.your_company.id)], limit=1)
        cls.your_company.write({'name': 'Odoo SA',
                                'country_id': cls.env.ref('base.be').id,
                                'street': 'Chaussée de Namur 40',
                                'street2': False,
                                'state_id': False,
                                'city': 'Ramillies',
                                'zip': 1367,
                                'phone': '081813700',
                                })
        # deco_art will be in europe
        cls.eu_partner = cls.env['res.partner'].create({
            'name': 'Deco Addict',
            'is_company': True,
            'street': '77 Santa Barbara Rd',
            'city': 'Pleasant Hill',
            'country_id': cls.env.ref('base.nl').id,
            'zip': '1105AA',
            'state_id': False,
            'email': 'deco.addict82@example.com',
            'phone': '(603)-996-3829',
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
            'name': 'Door with wings',
            'type': 'consu',
            'weight': 6.0,
        })

        cls.product_to_ship2 = cls.env["product.product"].create({
            'name': 'Door with Legs',
            'type': 'consu',
            'weight': 12.0,
        })

        shipping_product = cls.env['product.product'].create({
            'name': 'SendCloud Delivery',
            'type': 'service',
        })

        cls.sendcloud = cls.env['delivery.carrier'].create({
            'delivery_type': 'sendcloud',
            'product_id': shipping_product.id,
            'sendcloud_public_key': 'mock_key',
            'sendcloud_secret_key': 'mock_key',
            'name': 'SendCloud',
        })

        cls.package_type = cls.env['stock.package.type'].create({
            'name': 'test package',
        })

        with _mock_sendcloud_call(cls.warehouse_id):
            api_res = cls.sendcloud._get_sendcloud()._get_shipping_products('BE')
            user_chosen_product = cls._set_product_local_cache(cls, api_res[0])  # only grab the first response and apply client-side transformations
            cls.sendcloud._set_sendcloud_products(user_chosen_product, False)

    def _set_product_local_cache(self, sc_product):

        def humanize(tech_name):
            return str(tech_name).replace('_', ' ').capitalize()

        sc_product['local_cache'] = {
            'functionalities': {
                'bool_func': [],
                'detail_func': {},
                'customizable': {},
            }
        }

        func_cache = sc_product['local_cache']['functionalities']
        for key, values in sc_product['available_functionalities'].items():
            name = humanize(key)
            # Values is always of type List
            if any(isinstance(v, bool) and v for v in values):
                func_cache['bool_func'].append(name)
            else:
                for v in values:
                    if not (isinstance(v, bool) and not v) and (len(values) > 1 or v is not None):
                        humanized_value = 'None' if v is not None else humanize(v)
                        func_cache['detail_func'].get('name', []).append(humanized_value)
                if 'name' in func_cache['detail_func']:
                    func_cache['detail_func']['name'] = ', '.join(func_cache['detail_func']['name'])
            if len(values) > 1:
                func_cache['customizable'][key] = values

        return sc_product

    def test_deliver_inside_eu(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.eu_partner.id,
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
            'carrier_id': self.sendcloud.id,
            'order_id': sale_order.id
        })
        with _mock_sendcloud_call(self.warehouse_id):
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for shipment.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")
            picking.action_assign()
            self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.sendcloud_parcel_ref, False,
                             "SendCloud Parcel Id not set")

    def test_deliver_outside_eu(self):
        '''
            Same workflow as inside EU but tests other inner workings of sendcloud service
        '''
        sale_order = self.env['sale.order'].create({
            'partner_id': self.us_partner.id,
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
            'carrier_id': self.sendcloud.id,
            'order_id': sale_order.id
        })
        with _mock_sendcloud_call(self.warehouse_id):
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for ups shipment.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")
            picking.action_assign()
            self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.sendcloud_parcel_ref, False,
                             "SendCloud Parcel Id not set")

    def test_rate_shipment(self):
        """ Unit Test
        In Weight : 1 pkg of id in {1,2}
        Overweight : N pkg of id 3
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.eu_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id,
                }),
                Command.create({
                    'product_id': self.product_to_ship2.id,
                }),
            ]
        })
        with _mock_sendcloud_call(self.warehouse_id):
            res1 = self.sendcloud.with_context(order_weight=5.0).sendcloud_rate_shipment(sale_order)
            res2 = self.sendcloud.with_context(order_weight=15.0).sendcloud_rate_shipment(sale_order)
            res3 = self.sendcloud.with_context(order_weight=30.0).sendcloud_rate_shipment(sale_order)

        self.assertAlmostEqual(res1['price'], 1.1, places=2)
        self.assertAlmostEqual(res2['price'], 2.2, places=2)
        self.assertAlmostEqual(res3['price'], 4.4, places=2)  # 2 packages with method_id 2
        self.assertIsNotNone(res3['warning_message'])

    def test_user_filters(self):
        """
        Unit test
        """
        self.sendcloud.sendcloud_product_functionalities = {
            'signature': [True],
        }
        api = self.sendcloud._get_sendcloud()
        with _mock_sendcloud_call(self.warehouse_id):
            methods = api._get_shipping_methods(self.sendcloud, 'BE', 'BE')
            self.assertEqual(methods[0]['id'], 3)

    def test_partial_shipment(self):
        """ Functional Test
        SO -> Picking
        Partial picking
        Partial qty
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.eu_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id,
                    'product_uom_qty': 2.0,
                }),
                Command.create({
                    'product_id': self.product_to_ship2.id,
                    'product_uom_qty': 1.0,
                }),
            ]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.sendcloud.id,
            'order_id': sale_order.id,
        })
        with _mock_sendcloud_call(self.warehouse_id):
            api = self.sendcloud._get_sendcloud()
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for ups shipment.")
            picking = sale_order.picking_ids[0]
            # Assign Qty Done
            picking.action_assign()
            for move_line in picking.move_line_ids:
                move_line.quantity = move_line.quantity / 2.0
            picking.move_ids.picked = True
            picking.move_ids._action_done()
            self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")
            # Create parcels
            sender_id = api._get_pick_sender_address(picking)
            parcels = api._prepare_parcel(picking, sender_id, is_return=False)

        # Check qty & total weight in parcel(s)
        # qty in DeliveryPackage commodities are rounded (integer)
        items = parcels[0].get('parcel_items', [])
        self.assertEqual(items[0].get('quantity'), 1)
        self.assertEqual(items[1].get('quantity'), 1)
        self.assertAlmostEqual(12, float(parcels[0].get('weight')))

    def test_multicollo(self):
        """ Functional Test
        Single batch
        """
        self.sendcloud.sendcloud_use_batch_shipping = True

        sale_order = self.env['sale.order'].create({
            'partner_id': self.eu_partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_to_ship1.id,
                    'product_uom_qty': 2.0,
                }),
                Command.create({
                    'product_id': self.product_to_ship2.id,
                    'product_uom_qty': 1.0,
                }),
            ]
        })
        wiz_action = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'carrier_id': self.sendcloud.id,
            'order_id': sale_order.id,
        })
        with _mock_sendcloud_call(self.warehouse_id):
            api = self.sendcloud._get_sendcloud()
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()
            sale_order.action_confirm()
            self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate pickings for ups shipment.")
            picking = sale_order.picking_ids[0]
            picking.action_assign()
            # Create packages
            picking.move_ids[0].quantity_done = 2.0
            wiz_action = picking.action_put_in_pack()
            put_in_pack = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
                'delivery_package_type_id': self.package_type.id,
            })
            put_in_pack._compute_weight_uom_name()
            put_in_pack._compute_shipping_weight()
            put_in_pack.action_put_in_pack()
            picking.move_ids[1].quantity_done = 1.0
            wiz_action = picking.action_put_in_pack()
            put_in_pack = self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
                'delivery_package_type_id': self.package_type.id,
            })
            put_in_pack._compute_weight_uom_name()
            put_in_pack._compute_shipping_weight()
            put_in_pack.action_put_in_pack()

            picking.move_ids._action_done()
            self.assertGreater(picking.weight, 0.0, "Picking weight should be positive.")
            # Create parcels
            sender_id = api._get_pick_sender_address(picking)
            parcels = api._prepare_parcel(picking, sender_id, is_return=False)

        # Check qty & total weight in parcel(s)
        # qty in DeliveryPackage commodities are rounded (integer)
        self.assertEqual(len(parcels), 1)
        parcel = parcels[0]
        self.assertEqual(parcel.get('quantity'), 2)
        self.assertEqual(parcel.get('shipment', {}).get('id'), 2)
        self.assertAlmostEqual(24, float(parcel.get('weight')))
