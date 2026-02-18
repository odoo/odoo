# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
# import math
from requests.exceptions import RequestException
from werkzeug.urls import url_join

from odoo import _
from odoo.exceptions import UserError
# from odoo.tools import format_date


class Shipper:

    def __init__(self, api_key, prod_environment, logger):
        self.logger = logger
        self.session = requests.Session()
        if prod_environment:
            self.base_url = 'https://merchant-api-sandbox.shipper.id/v3/'  # Sandbox URL for now
        else:
            self.base_url = 'https://merchant-api-sandbox.shipper.id/v3/'
        self.session.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-API-Key': api_key,
        }

    def _send_request(self, endpoint, method='GET', data=None, params=None):
        """ Send a request to the shipper api at the given endpoint, with the given method and data.
        Returns the response, and use some basic error handling to raise a UserError if something went wrong.
        """
        url = url_join(self.base_url, endpoint)
        self.logger(f'{url}\n{method}\n{data}\n{params}', f'shipper request {endpoint}')
        if method not in ['GET', 'POST', 'DELETE']:
            raise Exception(f'Unhandled request method {method}')
        try:
            res = self.session.request(method=method, url=url, json=data, params=params, timeout=15)
            self.logger(f'{res.status_code} {res.text}', f'shipper response {endpoint}')
            res = res.json()
            metadata = res.get('metadata')
        except (RequestException, ValueError) as err:
            self.logger(str(err), f'shipper response {endpoint}')
            raise UserError(_('Something went wrong, please try again later: %s', err))

        http_status_code = metadata.get('http_status_code')

        if http_status_code == 403:
            raise UserError(_('Invalid shipper credentials.'))
        elif http_status_code not in [200, 201]:
            # Display detailed error messages if available
            error_message = 'An unknown error occurred.'
            if metadata.get('errors'):
                error_details = metadata['errors'][0]
                error_message = f"{error_details.get('message', 'No error message provided.')} (Code: {error_details.get('code')})"
            elif metadata.get('http_status'):
                error_message = metadata['http_status']
            raise UserError(_('Shipper returned an error: %s') % error_message)

        return res

    def _get_area_id(self, partner):
        self._validate_partner_fields(partner)
        keyword = partner.area_id.name
        return self._send_request(
            'location',
            method='GET',
            params={
                'adm_level': '5',
                'keyword': keyword
            }
        )

    def _rate_shipment(self, packages, origin_id, destination_id, order=False, picking=False):
        payload = {
            'origin': {
                'area_id': origin_id,
            },
            'destination': {
                'area_id': destination_id,
            },
            'for_order': True,
            'height': packages.get('estimated_dimension'),
            'length': packages.get('estimated_dimension'),
            'width': packages.get('estimated_dimension'),
            'weight': packages.get('total_weight'),
            'item_value': order.amount_total,
            "sort_by": [
                "final_price"
            ]
        }

        response = self._send_request('pricing/domestic', method='POST', data=payload)
        rate_list = []

        for rate_data in response.get("data", {}).get("pricings", []):
            logistic = rate_data.get("logistic", {})
            rate = rate_data.get("rate", {})

            rate_list.append({
                'rate_id': rate.get("id"),
                'carrier_name': logistic.get("name"),
                'rate_type': rate.get("type"),
                'service': rate.get("name"),
                'is_hubless': rate.get("is_hubless"),
                'final_price': rate_data.get("final_price"),
                'delivery_time': f"{rate_data.get('min_day')} - {rate_data.get('max_day')} days",
                'must_use_insurance': rate_data.get("must_use_insurance"),
                'insurance_fee': rate_data.get("insurance_fee"),
                'logo_url': logistic.get("logo_url"),
            })
        return rate_list

    def _create_orders(self, carrier, picking, package_info, origin_id, destination_id, rate_id, is_return=False):
        consignee = {
            "name": picking.partner_id.name,
            "phone_number": picking.partner_id.phone_sanitized,
        }
        consigner = {
            "name": carrier.shipper_origin_address.name,
            "phone_number": carrier.shipper_origin_address.phone_sanitized,
        }
        courier = {
            "cod": False,
            "rate_id": int(rate_id),
        }
        destination = {
            "address": picking.partner_id.shipper_complete_address,
            "area_id": destination_id,
        }
        origin = {
            "address": carrier.shipper_origin_address.shipper_complete_address,
            "area_id": origin_id,
        }
        items = []
        total_price = 0
        for move in picking.move_ids:
            total_price += move.product_id.list_price
            items.append({
                "name": move.product_id.name,
                "price": int(move.product_id.list_price),
                "qty": int(move.quantity),
            })

        # TODO: coverage, payment_type, package_type, allow user to choose (?)
        # Some request data doesn't allow float for some reason
        payload = {
            "consignee": consignee,
            "consigner": consigner,
            "destination": destination,
            "origin": origin,
            "service_type": 1,
            "courier": courier,
            "coverage": "domestic",
            # "external_id": picking.name,
            "package": {
                "height": package_info.get('estimated_dimension'),
                "items": items,
                "length": package_info.get('estimated_dimension'),
                "package_type": 2,
                "price": int(total_price),
                "weight": package_info.get('total_weight'),
                "width": package_info.get('estimated_dimension'),
            },
            "payment_type": "postpay"
        }
        return self._send_request('order', method='POST', data=payload)

    def _cancel_order(self, order_id, reason):
        payload = {
            "reason": reason
        }
        endpoint = 'order/' + order_id
        return self._send_request(endpoint, method='DELETE', params=order_id, data=payload)

    # Shipper actually allows multiple pickup request at one, max 30
    def _request_pickup(self, order_id):
        payload = {
            "data": {
                "order_activation": {
                    "order_id": [
                        order_id
                    ]
                }
            }
        }
        return self._send_request('pickup', method='POST', data=payload)

    def _get_shipping_label(self, order_id):
        payload = {
            "id": [
                order_id
            ],
            "type": "LBL"
        }
        return self._send_request('order/label', method='POST', data=payload)

    @staticmethod
    def _validate_partner_fields(partner):
        """ Make sure that the essential fields are filled in """
        required_address_fields = ['street', 'city', 'zip', 'country_id', 'state_id', 'city_id', 'district_id', 'area_id']
        fields_details = partner.fields_get(required_address_fields, ['string'])
        for field in required_address_fields:
            if not partner[field]:
                field_name = fields_details[field]['string']
                raise UserError(_('Please fill in the fields %s on %s.', field_name, partner.name))
