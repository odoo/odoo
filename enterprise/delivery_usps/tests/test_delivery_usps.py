# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged


_logger = logging.getLogger(__name__)
country_unavailable_msg = 'USPS temporary unavailable in %s, test aborted.'
country_unavailable_re = re.compile(
    r'No services available\.\n'
    r'At this time, all mail services to (\w+) are not available\.')


@tagged('-standard', 'external')
class TestDeliveryUSPS(TransactionCase):

    def setUp(self):
        super(TestDeliveryUSPS, self).setUp()

        self.iPadMini = self.env.ref('product.product_product_6')

        # Add a full address to "Your Company"
        self.your_company = self.env.ref('base.main_partner')
        self.your_company.write({'country_id': self.env.ref('base.us').id,
                                 'state_id': self.env.ref('base.state_us_5').id,
                                 'city': 'San Francisco',
                                 'street': '51 Federal Street',
                                 'zip': '94107',
                                 'phone': 9874582356})
        self.agrolait = self.env['res.partner'].create({
            'name': 'Agrolait',
            'phone': '(603)-996-3829',
            'street': "rue des Bourlottes, 9",
            'street2': "",
            'city': "Ramillies",
            'zip': 1367,
            'state_id': False,
            'country_id': self.env.ref('base.be').id,
        })
        self.think_big_system = self.env['res.partner'].create({
            'name': 'Think Big Systems',
            'phone': 3132223456,
            'street': '1 Infinite Loop',
            'street2': 'Tower 2',
            'city': 'Cupertino',
            'state_id': self.env.ref('base.state_us_13').id,
            'country_id': self.env.ref('base.us').id,
            'zip': '95014-2083'
        })
        # additional test address for Canada
        self.quebec = self.env.ref('base.state_ca_qc')
        self.montreal = self.env['res.partner'].create({'name': 'Vieux-Port de Montreal',
                                                        'street': '333 Rue de la Commune O',
                                                        'city': 'Montreal',
                                                        'zip': 'H2Y2E2',
                                                        'state_id': self.quebec.id,
                                                        'country_id': self.env.ref('base.ca').id})
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')

    def test_01_usps_basic_us_domestic_flow(self):
        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] Large Cabinet",
                    'product_uom': self.env.ref('uom.product_uom_unit').id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        so_vals = {'partner_id': self.think_big_system.id,
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.env.ref('delivery_usps.delivery_carrier_usps_domestic').id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        try:
            choose_delivery_carrier.update_price()
        except UserError as exc:
            m = country_unavailable_re.search(exc.args[0])
            if m:
                _logger.warning(country_unavailable_msg, m.group(1))
                return
            raise
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "USPS delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.move_ids[0].quantity = 1.0
        picking.move_ids[0].picked = True
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "USPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "USPS carrying price is probably incorrect")

        picking.cancel_shipment()

        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_02_usps_basic_international_flow(self):
        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] Large Cabinet",
                    'product_uom': self.env.ref('uom.product_uom_unit').id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        so_vals = {'partner_id': self.agrolait.id,
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.env.ref('delivery_usps.delivery_carrier_usps_international').id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        try:
            choose_delivery_carrier.update_price()
        except UserError as exc:
            m = country_unavailable_re.search(exc.args[0])
            if m:
                _logger.warning(country_unavailable_msg, m.group(1))
                return
            raise
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "USPS delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.move_ids[0].quantity = 1.0
        picking.move_ids[0].picked = True
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "USPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "USPS carrying price is probably incorrect")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_03_usps_ship_to_canada_flow(self):
        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] Large Cabinet",
                    'product_uom': self.env.ref('uom.product_uom_unit').id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        so_vals = {'partner_id': self.montreal.id,
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.env.ref('delivery_usps.delivery_carrier_usps_international').id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        try:
            choose_delivery_carrier.update_price()
        except UserError as exc:
            m = country_unavailable_re.search(exc.args[0])
            if m:
                _logger.warning(country_unavailable_msg, m.group(1))
                return
            raise
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "USPS delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sale Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.move_ids[0].quantity = 1.0
        picking.move_ids[0].picked = True
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "USPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "USPS carrying price is probably incorrect")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_04_usps_flow_from_delivery_order(self):
        StockPicking = self.env['stock.picking']

        order1_vals = {
                    'product_id': self.iPadMini.id,
                    'name': "[A1232] iPad Mini",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id}

        do_vals = { 'partner_id': self.agrolait.id,
                    'carrier_id': self.env.ref('delivery_usps.delivery_carrier_usps_international').id,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'state': 'draft',
                    'move_ids_without_package': [(0, None, order1_vals)]}

        delivery_order = StockPicking.create(do_vals)
        self.assertEqual(delivery_order.state, 'draft', 'Shipment state should be draft.')

        delivery_order.action_confirm()
        self.assertEqual(delivery_order.state, 'assigned', 'Shipment state should be ready(assigned).')
        delivery_order.move_ids_without_package.quantity = 1.0

        try:
            delivery_order.button_validate()
        except UserError as exc:
            m = country_unavailable_re.search(exc.args[0])
            if m:
                _logger.warning(country_unavailable_msg, m.group(1))
                return
            raise
        self.assertEqual(delivery_order.state, 'done', 'Shipment state should be done.')
