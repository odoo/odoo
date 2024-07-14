# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import re
import requests

from collections import defaultdict
from datetime import datetime, timedelta
from werkzeug.urls import url_join

from odoo import fields, _
from odoo.exceptions import ValidationError, UserError, RedirectWarning

_logger = logging.getLogger(__name__)


class ShipRocket:

    def __init__(self, carrier, debug_logger):
        """
        Initial parameters for making api requests.
        """
        self.url = 'https://apiv2.shiprocket.in/v1/'
        self.session = requests.Session()
        self.carrier = carrier
        self.debug_logger = debug_logger

    def _make_api_request(self, endpoint, method='GET', data=None, token=None):
        """
        make an api call, return response for multiple api requests of shiprocket
        """
        headers = {'Content-Type': 'application/json'}
        if token:
            # Include authorization header if a token is provided
            headers['Authorization'] = 'Bearer {}' .format(token)
        access_url = url_join(self.url, endpoint)
        try:
            # Log the request details for debugging purposes
            self.debug_logger("%s\n%s\n%s" % (access_url, method, data), 'shiprocket_request_%s' % endpoint)
            # Make the API request
            response = self.session.request(method, access_url, json=data, headers=headers, timeout=30)
            # Parse the response as JSON
            response_json = response.json()
            # Log the response details for debugging purposes
            self.debug_logger("%s\n%s" % (response.status_code, response.text), 'shiprocket_response_%s' % endpoint)
            return response_json
        except requests.exceptions.ConnectionError as error:
            _logger.warning('Connection Error: %s with the given URL: %s', error, access_url)
            return {'errors': {'timeout': "Cannot reach the server. Please try again later."}}
        except json.decoder.JSONDecodeError as error:
            _logger.warning('JSONDecodeError: %s', error)
            return {'errors': {'JSONDecodeError': str(error)}}

    def _authorize_generate_token(self):
        """
        Generate an access token from shiprocket credentials.
        """
        data = {
            'email': self.carrier.shiprocket_email,
            'password': self.carrier.shiprocket_password,
        }
        return self._make_api_request('external/auth/login', 'POST', data)

    def _get_token(self):
        """
        Generate an access token for shiprocket.
        The token is automatically generates after 9 days as it expires.
        """
        if not (self.carrier.shiprocket_email and self.carrier.shiprocket_password):
            action = self.carrier.env.ref('delivery.action_delivery_carrier_form')
            raise RedirectWarning(
                _("Please configure Shiprocket credentials in the shipping method"), action.id,
                _("Go to Shipping Method")
            )
        if not self.carrier.shiprocket_access_token or (
            self.carrier.shiprocket_token_valid_upto and
            self.carrier.shiprocket_token_valid_upto < fields.datetime.today()
        ):
            response_json = self._authorize_generate_token()
            if 'token' in response_json:
                self.carrier.write({
                    'shiprocket_access_token': response_json['token'],
                    'shiprocket_token_valid_upto': fields.datetime.today() + timedelta(days=9)
                })
        return self.carrier.shiprocket_access_token

    def _shiprocket_get_error_message(self, json_data):
        """
        Return error message(s) from shiprocket requests.
        """
        errors = json_data.get('errors', {})
        payload = json_data.get('payload', {})
        message = ''

        if errors:
            for value in errors.values():
                sub_msg = "\n".join(value) if isinstance(value, list) else value or ''
                message += _("Shiprocket Error: %s", sub_msg) + '\n'
        elif 'message' in json_data:
            message = _("Shiprocket Error: %s", json_data['message'])
        elif 'error_message' in payload:
            message = _("Shiprocket Error: %s", payload['error_message'])
        elif 'awb_assign_error' in payload:
            message = _('Shiprocket Error: %s', payload['awb_assign_error'])
        elif not json_data.get('label_created') and 'response' in json_data:
            message = _('Shiprocket Error: %s', json_data['response'])
        return message

    def _fetch_shiprocket_channels(self):
        """
        Import all active channels from shiprocket requests.
        https://apiv2.shiprocket.in/v1/external/channels
        """
        channels_response = self._make_api_request('external/channels', token=self._get_token())
        if 'data' in channels_response:
            channels = {channel['name']: channel['id'] for channel in channels_response['data']}
            return channels
        raise ValidationError(self._shiprocket_get_error_message(channels_response))

    def _fetch_shiprocket_couriers(self):
        """
        Import all available courier service(s) from shiprocket requests.
        https://apiv2.shiprocket.in/v1/external/courier/courierListWithCounts
        """
        carriers_json = self._make_api_request('external/courier/courierListWithCounts', token=self._get_token())
        if 'courier_data' in carriers_json:
            return carriers_json['courier_data']
        raise ValidationError(self._shiprocket_get_error_message(carriers_json))

    def _get_rate(self, shipper, recipient, weight_in_kg, dimensions):
        """
        Fetch rate from Shiprocket API based on the parameters.
        """
        res = {'currency': 'INR'}
        is_india = recipient.country_id.code == 'IN' and shipper.country_id.code == 'IN'
        data = {
            'pickup_postcode': shipper.zip,
            'delivery_postcode': recipient.zip,
            'weight': weight_in_kg,
            'delivery_country': recipient.country_id.code,
            'length': dimensions.get('length'),
            'breadth': dimensions.get('width'),
            'height': dimensions.get('height')
        }
        if is_india:
            data['cod'] = self.carrier.shiprocket_payment_method == 'cod' and '1' or '0'
            rate_json = self._make_api_request('external/courier/serviceability/', data=data, token=self._get_token())
        else:
            data['cod'] = 0
            rate_json = self._make_api_request('external/courier/international/serviceability', data=data, token=self._get_token())
        if rate_json and rate_json.get('data'):
            available_couriers = rate_json['data'].get('available_courier_companies')
            recommended_by = ''
            selected_couriers = False
            for available_courier in available_couriers:
                if self.carrier.shiprocket_courier_ids:
                    if available_courier.get('courier_company_id') in self.carrier.shiprocket_courier_ids.mapped('courier_code'):
                        selected_couriers = available_courier
                        break
                else:
                    selected_couriers = available_courier
                    recommended_by = rate_json['data'].get('recommended_by', {}).get('title')
                    break
            if selected_couriers:
                rate = selected_couriers.get('rate')
                if rate and isinstance(rate, dict):
                    rate = rate.get('rate')
                courier_name = selected_couriers.get('courier_name')
                courier_code = selected_couriers.get('courier_company_id')
                res.update({
                    'courier_name': courier_name,
                    'price': rate,
                    'courier_code': courier_code,
                    'warning_message': recommended_by and
                                       _("Courier (%s): %s", recommended_by, courier_name) or
                                       _("Courier: %s", courier_name)
                })
            else:
                res.update({'error_found': _('Courier is not available for delivery!')})
        else:
            res.update({'error_found': self._shiprocket_get_error_message(rate_json)})
        return res

    def _rate_request(self, recipient, shipper, order=False, picking=False, package=False):
        """
        Returns the dictionary of shipment rate from shiprocket
        https://apiv2.shiprocket.in/v1/external/courier/serviceability/
        https://apiv2.shiprocket.in/v1/external/courier/international/serviceability
        """
        if not (order or picking):
            raise UserError(_('Sale Order or Picking is required to get rate.'))
        products = picking and picking.move_ids.product_id or order.order_line.product_id
        self._check_required_value(
            recipient, shipper,
            products and products.filtered(lambda p: p.detailed_type in ['consu', 'product'])
        )
        if package:
            total_weight = package.weight
            dimensions = package.dimension
        else:
            default_package = self.carrier.shiprocket_default_package_type_id
            if picking:
                packages = self.carrier._get_packages_from_picking(picking, default_package)
            else:
                packages = self.carrier._get_packages_from_order(order, default_package)

            dimensions = {}
            if len(packages) == 1:
                dimensions = {
                    'length': packages[0].dimension['length'],
                    'width': packages[0].dimension['width'],
                    'height': packages[0].dimension['height']
                }
            total_weight = sum(pack.weight for pack in packages)
        weight_in_kg = self.carrier._shiprocket_convert_weight(total_weight)
        rate_dict = self._get_rate(shipper, recipient, weight_in_kg, dimensions)
        return rate_dict

    def _get_currency_converted_amount(self, amount, picking):
        """
        Returns the amount converted in INR currency.
        """
        inr_currency = picking.env.ref('base.INR')
        picking_currency = picking.sale_id.currency_id if picking.sale_id else picking.company_id.currency_id
        if picking_currency.id != inr_currency.id:
            return picking_currency._convert(amount, inr_currency, picking.company_id or picking.env.company,
                                             picking.date_done or datetime.today())
        return amount

    def _get_gst_tax_rate(self, stock_move):
        """
        Returns the GST tax amount from order lines.
        """
        gst_tax_amount = 0.0
        tax_ids = stock_move.sale_line_id and stock_move.sale_line_id.sudo().tax_id or stock_move.product_id.sudo().taxes_id
        for tax in tax_ids.flatten_taxes_hierarchy():
            tax_tag_ids = tax.invoice_repartition_line_ids.tag_ids
            if tax_tag_ids and any(tax.env.ref(f"l10n_in.tax_tag_{gst}gst", False) in tax_tag_ids for gst in ["c", "s", "i"]):
                gst_tax_amount += tax.amount
        return gst_tax_amount

    def _get_subtotal(self, line_vals):
        """
        Returns the subtotal of the order.
        """
        return sum(line['selling_price'] * line['units'] for line in line_vals)

    def _get_phone(self, partner):
        """
        Return the mobile/phone for shiprocket requests.
        """
        matches = re.findall(r"\d+", partner.mobile or partner.phone or '')
        return "".join(matches)

    def _get_shipping_lines(self, package, picking):
        """
        Returns shipping products data from picking to create an order.
        Get shipping lines from package commodities.
        """
        line_by_product = {}
        package_total_value = 0
        for commodity in package.commodities:
            moves = picking.env['stock.move']
            for move in picking.move_ids:
                if move.product_id != commodity.product_id:
                    continue
                if package.name == "Bulk Content":
                    if any(not ml.result_package_id for ml in move.move_line_ids):
                        moves |= move
                else:
                    if any(ml.result_package_id.name == package.name for ml in move.move_line_ids):
                        moves |= move
            dest_moves = picking.env['stock.move']
            for move in picking.move_ids:
                move_dest = move._rollup_move_dests(set())
                if move_dest:
                    # need only those moves which have sale_line_id links for 3 step delivery
                    dest_moves |= picking.env['stock.move'].browse(move_dest)
            if dest_moves:
                moves = dest_moves
            # label price must be in the INR currency
            unit_price = self._get_currency_converted_amount(round(commodity.monetary_value, 2), package.picking_id)
            line_by_product[commodity.product_id.id] = {
                "name": commodity.product_id.name,
                "sku": commodity.product_id.default_code or "",
                "units": commodity.qty,
                "selling_price": unit_price,
                "hsn": commodity.product_id.hs_code or "",
                "tax": self._get_gst_tax_rate(moves),
            }
            package_total_value += unit_price * commodity.qty
        if package_total_value > 50000 and not picking.eway_bill_number:
            raise ValidationError(_(
                'Eway Bill number is required to ship an order if order amount is more than 50,000 INR.'
            ))
        return line_by_product

    def _prepare_parcel(self, picking, package, courier_code=False, ship_charges=0.00, index=1):
        """
        Prepare parcel for picking shipment based on the package.
        """
        database_uuid = picking.env['ir.config_parameter'].sudo().get_param('database.uuid')
        unique_ref = str(index) + '-' + database_uuid[:5]
        order_name = picking.name
        partner = partner_invoice = picking.partner_id
        if partner.child_ids.filtered(lambda p: p.type == 'invoice'):
            partner_invoice = partner.child_ids.filtered(lambda p: p.type == 'invoice')[0]
        warehouse_partner_id = picking.picking_type_id.warehouse_id.partner_id or picking.company_id.partner_id
        warehouse_partner_name = re.sub(r'[^a-zA-Z0-9\s]+', '', warehouse_partner_id.name)[:36]
        if picking.sale_id:
            partner_invoice = picking.sale_id.partner_invoice_id
            order_name = order_name + '-' + picking.sale_id.name
        dimensions = package.dimension
        net_weight_in_kg = self.carrier._shiprocket_convert_weight(package.weight)
        line_vals = self._get_shipping_lines(package, picking).values()
        payment_method = "Prepaid" if self.carrier.shiprocket_payment_method == "prepaid" else "COD"
        return {
            "request_pickup": self.carrier.shiprocket_pickup_request,
            "print_label": True,
            "generate_manifest": self.carrier.shiprocket_manifests_generate,
            "order_id": order_name + '#' + unique_ref,
            "order_date": (picking.sale_id.date_order or picking.scheduled_date.date()).strftime("%Y-%m-%d"),
            "channel_id": self.carrier.shiprocket_channel_id.channel_code,
            "length": dimensions.get('length'),
            "breadth": dimensions.get('width'),
            "height": dimensions.get('height'),
            "weight": net_weight_in_kg,
            "courier_id": courier_code,
            "ewaybill_no": picking.eway_bill_number,
            "company_name": partner_invoice.commercial_partner_id.name,
            "billing_customer_name": partner_invoice.name,
            "billing_last_name": "",
            "billing_address": partner_invoice.street,
            "billing_address_2": partner_invoice.street2 or "",
            "billing_city": partner_invoice.city or "",
            "billing_pincode": partner_invoice.zip,
            "billing_state": partner_invoice.state_id.name or "",
            "billing_country": partner_invoice.country_id.name,
            "billing_email": partner_invoice.email,
            "billing_phone": self._get_phone(partner_invoice),
            "shipping_is_billing": partner_invoice == partner,
            "shipping_customer_name": partner.name,
            "shipping_last_name": "",
            "shipping_address": partner.street or "",
            "shipping_address_2": partner.street2 or "",
            "shipping_city": partner.city or "",
            "shipping_pincode": partner.zip,
            "shipping_country": partner.country_id.name,
            "shipping_state": partner.state_id.name or "",
            "shipping_email": partner.email,
            "shipping_phone": self._get_phone(partner),
            "order_items": list(line_vals),
            "sub_total": self._get_subtotal(line_vals),
            "payment_method": payment_method,
            "shipping_charges": ship_charges,
            "pickup_location": warehouse_partner_name,
            "vendor_details": {
                "email": warehouse_partner_id.email,
                "phone": self._get_phone(warehouse_partner_id),
                "name": warehouse_partner_name,
                "address": warehouse_partner_id.street,
                "address_2": warehouse_partner_id.street2 or "",
                "city": warehouse_partner_id.city or "",
                "state": warehouse_partner_id.state_id.name or "",
                "country": warehouse_partner_id.country_id.name,
                "pin_code": warehouse_partner_id.zip,
                "pickup_location": warehouse_partner_name,
            }
        }

    def _get_shipping_params(self, picking):
        """
        Returns the shipping data from picking for create an shiprocket order.
        """
        if not self.carrier.shiprocket_channel_id:
            action = self.carrier.env.ref('delivery.action_delivery_carrier_form')
            raise RedirectWarning(_("Configure Shiprocket channel in shipping method"), action.id,
                                  _("Go to Shipping Methods"))
        parcel_dict = {}
        ship_from = picking.picking_type_id.warehouse_id.partner_id or picking.company_id.partner_id
        default_package = self.carrier.shiprocket_default_package_type_id
        packages = self.carrier._get_packages_from_picking(picking, default_package)
        for index, package in enumerate(packages):
            # fetch rate based on package weight and size
            rate_response = self._rate_request(picking.partner_id, ship_from, picking=picking, package=package)
            # need courier code, as the rate request and forward shipment APIs must have to use the same courier code.
            courier_code = rate_response.get('courier_code')
            # ship_charges is mandatory as forward shipment API will not return it in response, used in subtotal.
            ship_charges = rate_response.get('price')
            parcel = self._prepare_parcel(picking, package, courier_code, ship_charges, index=index)
            parcel_dict[package] = parcel
        return parcel_dict

    def _send_shipping(self, picking):
        """
        Returns the dictionary with order_id, shipment_id, tracking_number,
        exact_price and courier_name for delivery order.
        - for multiple package, shiprocket create new order.
        https://apiv2.shiprocket.in/v1/external/shipments/create/forward-shipment
        """
        products = picking.move_line_ids.product_id
        self._check_required_value(
            picking.partner_id,
            picking.picking_type_id.warehouse_id.partner_id or picking.company_id.partner_id,
            products and products.filtered(lambda p: p.detailed_type in ['consu', 'product'])
        )
        res = {
            'exact_price': 0.00,
            'tracking_numbers': [],
            'order_ids': [],
            'all_pack': defaultdict(lambda: {'response': {}, 'order_details': {}})
        }
        params = self._get_shipping_params(picking)
        for delivery_package, shiprocket_parcel in params.items():
            order_response = self._make_api_request(
                'external/shipments/create/forward-shipment', 'POST',
                shiprocket_parcel,
                token=self._get_token()
            )
            if order_response.get('errors'):
                picking.message_post(body=self._shiprocket_get_error_message(order_response))
                continue
            payload = order_response.get('payload')
            if not payload:
                picking.message_post(body=_('AWB assignment was unsuccessful: %s') % (self._shiprocket_get_error_message(order_response)))
                continue
            res['all_pack'][delivery_package]['response'] = payload
            if payload.get('shipment_id') and payload.get('error_message') and 'Oops! Cannot reassign courier' in payload['error_message']:
                payload.pop('error_message')
                res['all_pack'][delivery_package]['response']['warning_message'] = \
                    _("Same order is available in Shiprocket so label provided is the copy of existing one.")
                label_response = self._generate_label(payload['shipment_id'])
                res['all_pack'][delivery_package]['response']['label_url'] = label_response.get('label_url')
            if payload.get('shipment_id') and not payload.get('error_message') and not payload.get('awb_assign_error'):
                res['tracking_numbers'].append(payload.get('awb_code'))
                # To get exact_price
                order_details = self._make_api_request('external/shipments/{}'.format(payload['shipment_id']), token=self._get_token())
                order_id = order_details.get('data').get('order_id')
                if order_id:
                    res['order_ids'].append(str(order_id))
                res['all_pack'][delivery_package]['order_details'] = order_details
                res['exact_price'] += float(order_details.get('data', {}).get('charges', {}).get('freight_charges', '0.00'))
            else:
                picking.message_post(body=_('AWB assignment was unsuccessful: %s') % (self._shiprocket_get_error_message(order_response)))
        return res

    def _generate_label(self, shipment_id):
        """
        Generate Label for shiprocket order if the forward shipment fails
        to generate label again and shipment is already created in shiprocket.
        https://apiv2.shiprocket.in/v1/external/courier/generate/label
        """
        label_data = {"shipment_id": [shipment_id]}
        label_result = self._make_api_request(
            'external/courier/generate/label',
            'POST',
            label_data,
            token=self._get_token()
        )
        if label_result and 'label_url' in label_result:
            return label_result
        raise ValidationError(self._shiprocket_get_error_message(label_result))

    def _send_cancelling(self, orders_data, pickup_request):
        """
        Cancelling shiprocket order/shipment.
        https://apiv2.shiprocket.in/v1/external/orders/cancel
        https://apiv2.shiprocket.in/v1/external/orders/cancel/shipment/awbs
        """
        cancel_result = {}
        for order in orders_data:
            if pickup_request:
                endpoint = 'external/orders/cancel'
                data = {'ids': [order]}
            else:
                endpoint = 'external/orders/cancel/shipment/awbs'
                data = {'awbs': [order]}
            cancel_result.update({
                order: self._make_api_request(endpoint, 'POST', data, token=self._get_token()
            )})
        return cancel_result

    def _check_required_value(self, recipient, shipper, products):
        """
        Check if the required value are not present in order to process an API call.
        return True or return an error if configuration is missing.
        """
        error_msg = {'Customer': [], 'Shipper': []}
        if not recipient.street:
            error_msg['Customer'].append(_("Street is required!"))
        if not recipient.zip:
            error_msg['Customer'].append(_("Pincode is required!"))
        if not recipient.country_id:
            error_msg['Customer'].append(_("Country is required!"))
        if not recipient.email:
            error_msg['Customer'].append(_("Email is required!"))
        if not recipient.phone and not recipient.mobile:
            error_msg['Customer'].append(_("Phone or Mobile is required!"))
        if not shipper.street:
            error_msg['Shipper'].append(_("Street is required!"))
        if not shipper.zip:
            error_msg['Shipper'].append(_("Pincode is required!"))
        if not shipper.country_id:
            error_msg['Shipper'].append(_("Country is required!"))
        if not shipper.email:
            error_msg['Shipper'].append(_("Email is required!"))
        if not shipper.phone and not shipper.mobile:
            error_msg['Shipper'].append(_("Phone or Mobile is required!"))
        for product in products:
            if not product.weight:
                error_msg.setdefault(product.name, [])
                error_msg[product.name].append(_("Weight is missing!"))
            if not product.default_code:
                error_msg.setdefault(product.name, [])
                error_msg[product.name].append(_("SKU is missing!"))
        if error_msg:
            msg = "".join(e_for + "\n- " + "\n- ".join(e) + "\n" for e_for, e in error_msg.items() if e)
            if msg:
                raise ValidationError(msg)
        return True
