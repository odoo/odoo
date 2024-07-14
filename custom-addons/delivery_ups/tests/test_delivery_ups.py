# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import functools
from base64 import b64encode
from contextlib import contextmanager
from unittest.mock import Mock, patch

from odoo.tools import file_open
from odoo.tests.common import TransactionCase, tagged, Form


@tagged('-standard', 'external')
class TestDeliveryUPS(TransactionCase):

    def setUp(self):
        super(TestDeliveryUPS, self).setUp()
        self.iPadMini = self.env['product.product'].create({
            'name': 'Ipad Mini',
            'weight': 0.01,
        })
        self.large_desk = self.env['product.product'].create({
            'name': 'Large Desk',
            'weight': 0.01,
        })
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        # Add a full address to "Your Company" and "Agrolait"
        self.your_company = self.env.ref('base.main_partner')
        self.your_company.write({
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_5').id,
            'city': 'San Francisco',
            'street': '51 Federal Street',
            'zip': '94107',
            'phone': '+1 555-555-5555',
        })
        self.agrolait = self.env['res.partner'].create({
            'name': 'Agrolait',
            'phone': '(603)-996-3829',
            'country_id': self.env.ref('base.be').id,
            'city': 'Auderghem-Ouderghem',
            'street': 'Avenue Edmond Van Nieuwenhuyse',
            'zip': '1160'
        })
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')

    def wiz_put_in_pack(self, picking):
        """ Helper to use the 'choose.delivery.package' wizard
        in order to call the 'action_put_in_pack' method.
        """
        wiz_action = picking.action_put_in_pack()
        self.assertEqual(wiz_action['res_model'], 'choose.delivery.package', 'Wrong wizard returned')
        wiz = Form(self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'delivery_package_type_id': picking.carrier_id.ups_default_package_type_id.id
        }))
        choose_delivery_carrier = wiz.save()
        choose_delivery_carrier.action_put_in_pack()

    def test_01_ups_basic_flow(self):
        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] Large Cabinet",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        # Set service type = 'UPS Worldwide Expedited', which is available between US to BE
        carrier = self.env.ref('delivery_ups.delivery_carrier_ups_us')
        carrier.write({'ups_default_service_type': '08',
                       'ups_package_dimension_unit': 'IN'})
        carrier.ups_default_package_type_id.write({'height': '3',
                                                   'width': '3',
                                                   'packaging_length': '3'})

        so_vals = {'partner_id': self.agrolait.id,
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "UPS delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.move_ids[0].quantity = 1.0
        picking.move_ids[0].picked = True
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "UPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "UPS carrying price is probably incorrect")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_02_ups_multipackage_flow(self):
        SaleOrder = self.env['sale.order']

        # Set package type = 'Pallet' and service type = 'UPS Worldwide Express Freight'
        # so in this case height, width and length required.
        carrier = self.env.ref('delivery_ups.delivery_carrier_ups_us')
        carrier.write({'ups_default_package_type_id': self.env.ref('delivery_ups.ups_packaging_30').id,
                       'ups_default_service_type': '96',
                       'ups_package_dimension_unit': 'IN'})
        carrier.ups_default_package_type_id.write({'height': '3',
                                                   'width': '3',
                                                   'packaging_length': '3'})

        sol_1_vals = {'product_id': self.iPadMini.id,
                      'name': "[A1232] Large Cabinet",
                      'product_uom': self.uom_unit.id,
                      'product_uom_qty': 1.0,
                      'price_unit': self.iPadMini.lst_price}

        sol_2_vals = {'product_id': self.large_desk.id,
                      'name': "[A1090] Large Desk",
                      'product_uom': self.uom_unit.id,
                      'product_uom_qty': 1.0,
                      'price_unit': self.large_desk.lst_price}

        so_vals = {'partner_id': self.agrolait.id,
                   'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "UPS delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        move0 = picking.move_ids[0]
        move0.quantity = 1.0
        move0.picked = True
        self.wiz_put_in_pack(picking)
        move1 = picking.move_ids[1]
        move1.quantity = 1.0
        move1.picked = True
        self.wiz_put_in_pack(picking)
        self.assertEqual(len(picking.move_line_ids.mapped('result_package_id')), 2, "2 packages should have been created at this point")
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "UPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "UPS carrying price is probably incorrect")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_03_ups_flow_from_delivery_order(self):
        # Set service type = 'UPS Worldwide Expedited', which is available between US to BE
        carrier = self.env.ref('delivery_ups.delivery_carrier_ups_us')
        carrier.write({'ups_default_service_type': '08',
                       'ups_package_dimension_unit': 'IN'})
        carrier.ups_default_package_type_id.write({'height': '3',
                                                   'width': '3',
                                                   'packaging_length': '3'})

        StockPicking = self.env['stock.picking']

        order1_vals = {
                    'product_id': self.iPadMini.id,
                    'name': "[A1232] iPad Mini",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id}

        do_vals = { 'partner_id': self.agrolait.id,
                    'carrier_id': carrier.id,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'move_ids_without_package': [(0, None, order1_vals)]}

        delivery_order = StockPicking.create(do_vals)
        self.assertEqual(delivery_order.state, 'draft', 'Shipment state should be draft.')

        delivery_order.action_confirm()
        self.assertEqual(delivery_order.state, 'assigned', 'Shipment state should be ready(assigned).')
        delivery_order.move_ids_without_package.quantity = 1.0

        delivery_order.button_validate()
        self.assertEqual(delivery_order.state, 'done', 'Shipment state should be done.')

    def test_04_backorder_and_track_number(self):
        """ Suppose a two-steps delivery with 2 x Product A and 2 x Product B.
        For the Pick step, process a first picking (PICK01) with 2 x Product A
        and a backorder (PICK02) with 2 x Product B
        For the Out step, process a first picking (OUT01) with 1 x Product A
        and a backorder (OUT02) with 1 x Product A and 2 x Product B
        This test ensures that:
            - OUT01 and OUT02 have their own tracking reference
            - The tracking reference of PICK01 is defined with the one of OUT01 and OUT02
            - The tracking reference of PICK02 is defined with the one of OUT02
        """
        def process_picking(picking):
            action = picking.button_validate()
            if action is not True:
                wizard = Form(self.env[action['res_model']].with_context(action['context']))
                wizard.save().process()

        warehouse = self.env.user._get_default_warehouse_id()
        warehouse.delivery_steps = 'pick_ship'
        stock_location = warehouse.lot_stock_id

        carrier = self.env.ref('delivery_ups.delivery_carrier_ups_us')
        carrier.write({'ups_default_service_type': '08', 'ups_package_dimension_unit': 'IN'})
        carrier.ups_default_package_type_id.write({'height': '1', 'width': '1', 'packaging_length': '1'})

        product_a, product_b = self.env['product.product'].create([{
            'name': p_name,
            'weight': 1,
        } for p_name in ['Product A', 'Product B']])

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.agrolait
        with so_form.order_line.new() as line:
            line.product_id = product_a
            line.product_uom_qty = 2
        with so_form.order_line.new() as line:
            line.product_id = product_b
            line.product_uom_qty = 2
        so = so_form.save()

        # Add UPS shipping
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        choose_delivery_carrier.button_confirm()

        so.action_confirm()
        pick01 = so.picking_ids.filtered(lambda p: p.location_id == stock_location)
        out01 = so.picking_ids - pick01

        # First step with 2 x Product A
        pick01.move_ids.filtered(lambda m: m.product_id == product_a).write({'quantity': 2, 'picked': True})
        process_picking(pick01)
        # First step with 2 x Product B
        pick02 = pick01.backorder_ids
        process_picking(pick02)

        # Second step with 1 x Product A
        out01.move_ids.filtered(lambda m: m.product_id == product_a).write({'quantity': 1, 'picked': True})
        process_picking(out01)
        out02 = out01.backorder_ids
        self.assertTrue(out01.carrier_tracking_ref)
        self.assertFalse(out02.carrier_tracking_ref)
        self.assertEqual(pick01.carrier_tracking_ref, out01.carrier_tracking_ref)
        self.assertFalse(pick02.carrier_tracking_ref)

        # Second step with 1 x Product A + 2 x Product B
        process_picking(out02)
        self.assertTrue(out01.carrier_tracking_ref)
        self.assertTrue(out02.carrier_tracking_ref)
        self.assertEqual(pick01.carrier_tracking_ref, out01.carrier_tracking_ref + ',' + out02.carrier_tracking_ref)
        self.assertEqual(pick02.carrier_tracking_ref, out02.carrier_tracking_ref)


@functools.lru_cache(maxsize=1)
def get_rate_request():
    with file_open('delivery_ups/tests/rate_request.xml', 'rb') as rate_file:
        return rate_file.read()

@functools.lru_cache(maxsize=1)
def get_shipment_request():
    # Reconstruct the original shipment request here, we had extracted the
    # various base64 payloads into decidated files to access their content.
    with file_open('delivery_ups/tests/shipment_request.xml', 'rb') as shipment_file, \
         file_open('delivery_ups/tests/label1Z515VW96795112382.gif', 'rb') as label_gif_file, \
         file_open('delivery_ups/tests/label1Z515VW96795112382.html', 'rb') as label_html_file, \
         file_open('delivery_ups/tests/invoice.pdf', 'rb') as invoice_file:
        return (
            shipment_file.read()
            .replace(b'<!-- PLACEHOLDER LABEL GIF -->', b64encode(label_gif_file.read()))
            .replace(b'<!-- PLACEHOLDER LABEL HTML -->', b64encode(label_html_file.read()))
            .replace(b'<!-- PLACEHOLDER INVOICE -->', b64encode(invoice_file.read()))
        )

@functools.lru_cache(maxsize=1)
def get_void_shipment_request():
    with file_open('delivery_ups/tests/void_shipment_request.xml', 'rb') as void_shipment_file:
        return void_shipment_file.read()


@tagged('standard', '-external')
class TestMockDeliveryUPS(TestDeliveryUPS):

    @contextmanager
    def patch_ups_requests(self):
        """ Mock context for requests to the UPS API. """

        class MockedSession:
            def __init__(self, *args, **kwargs):
                self.headers = dict()

            def mount(self, *args, **kwargs):
                return None

            def close(self, *args, **kwargs):
                return None

            def post(self, *args, **kwargs):
                response = Mock()
                response.headers = {}
                response.status_code = 200
                if b'<ns0:RateRequest' in kwargs.get('data'):
                    response.content = get_rate_request()
                elif b'<ns0:ShipmentRequest' in kwargs.get('data'):
                    response.content = get_shipment_request()
                elif b'<ns0:VoidShipmentRequest' in kwargs.get('data'):
                    response.content = get_void_shipment_request()
                return response

        # zeep.Client.transport is using post from requests.Session
        with patch('zeep.transports.requests.Session') as mocked_session:
            mocked_session.side_effect = MockedSession
            yield mocked_session

    def test_01_ups_basic_flow(self):
        with self.patch_ups_requests():
            super().test_01_ups_basic_flow()

    def test_02_ups_multipackage_flow(self):
        with self.patch_ups_requests():
            super().test_02_ups_multipackage_flow()

    def test_03_ups_flow_from_delivery_order(self):
        with self.patch_ups_requests():
            super().test_03_ups_flow_from_delivery_order()

    def test_04_backorder_and_track_number(self):
        with self.patch_ups_requests():
            super().test_04_backorder_and_track_number()
