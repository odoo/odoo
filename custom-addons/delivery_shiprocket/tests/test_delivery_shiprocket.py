# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime
import re

from odoo.addons.delivery_shiprocket.models.shiprocket_request import ShipRocket
from odoo.tests import TransactionCase

_logger = logging.getLogger(__name__)


class TestDeliveryShiprocket(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.in_partner = cls.env["res.partner"].create({
            'name': 'Partner IN',
            'country_id': cls.env.ref('base.in').id,
            'street': '7, Vrajvatika',
            'street2': 'Metro piller no.119, Vastral',
            'state_id': cls.env.ref('base.state_in_gj').id,
            'city': 'Ahmedabad',
            'zip': 382418,
            'phone': '+91 9227411196',
            'email': 'partner@odoo.com'
        })
        cls.product_to_ship1 = cls.env["product.product"].create({
            'name': 'Door with wings',
            'type': 'consu',
            'weight': 0.1,
            'default_code': 'AHM1232',
            'lst_price': 100
        })
        cls.product_to_ship2 = cls.env["product.product"].create({
            'name': 'Door with Legs',
            'type': 'consu',
            'weight': 0.1,
            'default_code': 'AYD1233',
            'lst_price': 200
        })
        cls.shiprocket = cls.env.ref('delivery_shiprocket.delivery_carrier_shiprocket')
        cls.shiprocket.write({
            'shiprocket_default_package_type_id': cls.env.ref('delivery_shiprocket.shiprocket_packaging_box_1kg')
        })
        cls.database_uuid = cls.env['ir.config_parameter'].sudo().get_param('database.uuid')
        cls.order_date = str(datetime.today().date())

    def _get_expected_parcel_data(self):
        """
        Returns the expected parcel data for shiprocket requests.
        """
        return {
            'request_pickup': self.shiprocket.shiprocket_pickup_request,
            'print_label': True,
            'generate_manifest': self.shiprocket.shiprocket_manifests_generate,
            'order_id': '',
            'order_date': '',
            'channel_id': self.shiprocket.shiprocket_channel_id and self.shiprocket.shiprocket_channel_id.channel_code or 0,
            'length': 0,
            'breadth': 0,
            'height': 0,
            'weight': 0.0,
            'courier_id': 1,
            'ewaybill_no': False,
            'company_name': 'Partner IN',
            'billing_customer_name': 'Partner IN',
            'billing_last_name': '',
            'billing_address': '7, Vrajvatika',
            'billing_address_2': 'Metro piller no.119, Vastral',
            'billing_city': 'Ahmedabad',
            'billing_pincode': '382418',
            'billing_state': 'Gujarat',
            'billing_country': 'India',
            'billing_email': 'partner@odoo.com',
            'billing_phone': '919227411196',
            'shipping_is_billing': True,
            'shipping_customer_name': 'Partner IN',
            'shipping_last_name': '',
            'shipping_address': '7, Vrajvatika',
            'shipping_address_2': 'Metro piller no.119, Vastral',
            'shipping_city': 'Ahmedabad',
            'shipping_pincode': '382418',
            'shipping_country': 'India',
            'shipping_state': 'Gujarat',
            'shipping_email': 'partner@odoo.com',
            'shipping_phone': '919227411196',
            'order_items': [
                {
                    'name': '',
                    'sku': '',
                    'units': 0.0,
                    'selling_price': 0.0,
                    'hsn': '',
                    'tax': 0
                }
            ],
            'sub_total': 0,
            'payment_method': 'Prepaid' if self.shiprocket.shiprocket_payment_method == 'prepaid' else 'COD',
            'shipping_charges': 0.0,
            'pickup_location': 'My Company San Francisco',
            'vendor_details': {
                'email': 'info@yourcompany.com',
                'phone': '16505550111',
                'name': 'My Company San Francisco',
                'address': '250 Executive Park Blvd, Suite 3400',
                'address_2': '',
                'city': 'San Francisco',
                'state': 'California',
                'country': 'United States',
                'pin_code': '94134',
                'pickup_location': 'My Company San Francisco'
            }
        }

    def test_01_shiprocket_basic_in_default_package(self):
        SaleOrder = self.env['sale.order']
        sol_vals = {'product_id': self.product_to_ship1.id,
                    'name': "[AHM1232] Door with wings",
                    'product_uom': self.product_to_ship1.uom_id.id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.product_to_ship1.lst_price}

        so_vals = {'partner_id': self.in_partner.id,
                   'order_line': [(0, None, sol_vals)]}
        sale_order = SaleOrder.create(so_vals)
        # Add delivery cost in Sales order
        self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.shiprocket.id
        })
        sale_order.action_confirm()
        self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate a picking.")
        picking = sale_order.picking_ids[0]
        picking.move_line_ids[0].quantity = 1.0
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")
        picking.carrier_id = self.shiprocket.id
        sr = ShipRocket(self, picking.carrier_id.log_xml)
        sr.carrier = picking.carrier_id
        default_package = picking.carrier_id.shiprocket_default_package_type_id
        packages = picking.carrier_id._get_packages_from_picking(picking, default_package)
        for index, package in enumerate(packages):
            dimensions = package.dimension
            parcel_data = sr._prepare_parcel(picking, package, 1, 0.0, index=index)
            unique_ref = str(index) + '-' + self.database_uuid[:5]
            order_name = picking.name + '-' + picking.sale_id.name + '#' + unique_ref
            net_weight_in_kg = picking.carrier_id._shiprocket_convert_weight(package.weight)
            expected_parcel_data = self._get_expected_parcel_data()
            line_vals = sr._get_shipping_lines(package, picking).values()
            warehouse_partner_id = picking.picking_type_id.warehouse_id.partner_id or picking.company_id.partner_id
            warehouse_partner_name = re.sub(r'[^a-zA-Z0-9\s]+', '', warehouse_partner_id.name)
            expected_parcel_data.update({
                'order_id': order_name,
                'order_date': self.order_date,
                'length': dimensions.get('length'),
                'breadth': dimensions.get('width'),
                'height': dimensions.get('height'),
                'weight': net_weight_in_kg,
                'order_items': list(line_vals),
                'sub_total': sr._get_subtotal(line_vals),
                'pickup_location': warehouse_partner_name,
                'vendor_details': {
                    'email': warehouse_partner_id.email,
                    'phone': sr._get_phone(warehouse_partner_id),
                    'name': warehouse_partner_name,
                    'address': warehouse_partner_id.street,
                    'address_2': warehouse_partner_id.street2 or '',
                    'city': warehouse_partner_id.city or '',
                    'state': warehouse_partner_id.state_id.name or '',
                    'country': warehouse_partner_id.country_id.name,
                    'pin_code': warehouse_partner_id.zip,
                    'pickup_location': warehouse_partner_name
                }
            })
            self.assertDictEqual(parcel_data, expected_parcel_data, "Expected parcel data does not match with actual data!")

    def test_02_shiprocket_in_multi_package(self):
        SaleOrder = self.env['sale.order']
        sol_vals1 = {
            'product_id': self.product_to_ship1.id,
            'name': "[AHM1232] Door with wings",
            'product_uom': self.product_to_ship1.uom_id.id,
            'product_uom_qty': 3.0,
            'price_unit': self.product_to_ship1.lst_price}
        sol_vals2 = {
            'product_id': self.product_to_ship2.id,
            'name': "[AYD1233] Door with legs",
            'product_uom': self.product_to_ship2.uom_id.id,
            'product_uom_qty': 2.0,
            'price_unit': self.product_to_ship2.lst_price}

        so_vals = {'partner_id': self.in_partner.id,
                   'order_line': [(0, None, sol_vals1), (0, None, sol_vals2)]}
        sale_order = SaleOrder.create(so_vals)
        # Add delivery cost in Sales order
        self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.shiprocket.id
        })
        sale_order.action_confirm()
        self.assertGreater(len(sale_order.picking_ids), 0, "The Sales Order did not generate a picking.")
        picking = sale_order.picking_ids[0]
        picking.move_line_ids[0].quantity = 3.0
        picking.move_ids[0].picked = True
        picking.action_put_in_pack()
        picking.move_line_ids[1].quantity = 2.0
        picking.move_ids[1].picked = True
        picking.action_put_in_pack()
        picking.carrier_id = self.shiprocket.id
        sr = ShipRocket(self, picking.carrier_id.log_xml)
        sr.carrier = picking.carrier_id
        default_package = picking.carrier_id.shiprocket_default_package_type_id
        packages = picking.carrier_id._get_packages_from_picking(picking, default_package)
        warehouse_partner_id = picking.picking_type_id.warehouse_id.partner_id or picking.company_id.partner_id
        warehouse_partner_name = re.sub(r'[^a-zA-Z0-9\s]+', '', warehouse_partner_id.name)
        for index, package in enumerate(packages):
            parcel_data = sr._prepare_parcel(picking, package, 1, 0.0, index=index)
            dimensions = package.dimension
            unique_ref = str(index) + '-' + self.database_uuid[:5]
            order_name = picking.name + '-' + picking.sale_id.name + '#' + unique_ref
            net_weight_in_kg = picking.carrier_id._shiprocket_convert_weight(package.weight)
            expected_parcel_data = self._get_expected_parcel_data()
            line_vals = sr._get_shipping_lines(package, picking).values()
            expected_parcel_data.update({
                'order_id': order_name,
                'order_date': self.order_date,
                'length': dimensions.get('length'),
                'breadth': dimensions.get('width'),
                'height': dimensions.get('height'),
                'weight': net_weight_in_kg,
                'order_items': list(line_vals),
                'sub_total': sr._get_subtotal(line_vals),
                'pickup_location': warehouse_partner_name,
                'vendor_details': {
                    'email': warehouse_partner_id.email,
                    'phone': sr._get_phone(warehouse_partner_id),
                    'name': warehouse_partner_name,
                    'address': warehouse_partner_id.street,
                    'address_2': warehouse_partner_id.street2 or '',
                    'city': warehouse_partner_id.city or '',
                    'state': warehouse_partner_id.state_id.name or '',
                    'country': warehouse_partner_id.country_id.name,
                    'pin_code': warehouse_partner_id.zip,
                    'pickup_location': warehouse_partner_name
                }
            })
            self.assertDictEqual(parcel_data, expected_parcel_data, "Expected parcel data does not match with actual data!")
