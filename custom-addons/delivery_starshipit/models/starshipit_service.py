# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from requests.exceptions import RequestException
from werkzeug.urls import url_join

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import format_date

BASE_URL = 'https://api.starshipit.com/api/'


class Starshipit:

    def __init__(self, api_key, subscription_key, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers = {
            'Content-Type': 'application/json',
            'StarShipIT-Api-Key': api_key,
            'Ocp-Apim-Subscription-Key': subscription_key,
        }

    def _send_request(self, endpoint, method='GET', data=None, params=None, route=BASE_URL):
        """ Send a request to the starshipit api at the given endpoint, with the given method and data.
        Returns the response, and use some basic error handling to raise a UserError if something went wrong.
        """
        url = url_join(route, endpoint)
        self.logger(f'{url}\n{method}\n{data}\n{params}', f'starshipit request {endpoint}')
        if method not in ['GET', 'POST', 'DELETE']:
            raise Exception(f'Unhandled request method {method}')
        try:
            res = self.session.request(method=method, url=url, json=data, params=params, timeout=15)
            self.logger(f'{res.status_code} {res.text}', f'starshipit response {endpoint}')
            res = res.json()
        except (RequestException, ValueError) as err:
            self.logger(str(err), f'starshipit response {endpoint}')
            raise UserError(_('Something went wrong, please try again later: %s', err))

        if res.get('statusCode') == 403:
            raise UserError(_('Invalid Starshipit credentials.'))
        if res.get('statusCode') == 429:
            raise UserError(_('Starshipit API rate exceeded. Please try again later.'))
        if not res.get('success'):  # In case of errors from the api we can display the first issue to the user.
            message = ''
            if res.get('errors'):
                message = res['errors'][0]['details']
            elif res.get('message'):
                message = res['message']
            raise UserError(_('Starshipit returned an error: %(message)s', message=message))

        return res

    def _rate_shipment(self, packages, order=False, picking=False):
        """ Returns the rates for the given order for every available delivery service.
        The returned value is edited to return a dict with an easier structure to manipulate.
        """
        if order:
            warehouse_partner = order.warehouse_id.partner_id
            destination_partner = order.partner_shipping_id
            currency_id = order.currency_id or order.company_id.currency_id
        else:
            warehouse_partner = picking.picking_type_id.warehouse_id.partner_id
            destination_partner = picking.partner_id
            currency_id = picking.sale_id.currency_id or picking.company_id.currency_id
        payload = {
            'sender': {
                'street': warehouse_partner.street,
                'city': warehouse_partner.city,
                'state': warehouse_partner.state_id.code,
                'post_code': warehouse_partner.zip,
                'country_code': warehouse_partner.country_id.code,
            },
            'destination': {
                'street': destination_partner.street,
                'city': destination_partner.city,
                'state': destination_partner.state_id.code,
                'post_code': destination_partner.zip,
                'country_code': destination_partner.country_id.code,
            },
            'packages': packages,
            'currency': currency_id.name,
            'include_pricing': True,
        }
        result = self._send_request('rates', method='POST', data=payload)
        return {
            'success': result['success'],
            'rates': {rate['service_code']: rate for rate in result['rates']},
        }

    def _create_orders(self, carrier, pickings, is_return=False):
        """ Creates the orders in starshipit using the provided pickings. One order will be created for each picking.
        Orders are returned as a dict with the order_number being the keys.
        """
        orders = []

        for picking in pickings:
            starshipit_picking_number = self._get_starshipit_order_number(picking)
            if len(starshipit_picking_number) > 50:  # Very unlikely to happen, simply a security measure.
                raise UserError(_("The picking %(picking_name)s sequence is too long for Starshipit. "
                                  "Please update your pickings sequence in order to use at most 50 characters.",
                                  picking_name=starshipit_picking_number))
            if len(carrier.starshipit_service_code) > 100:
                raise UserError(_("The service code %(service_code)s is too long for Starshipit. "
                                  "Please update the code inside starshipit to be at most 100 characters, then "
                                  "update your shipping carrier %(shipping_carrier)s to the new code.",
                                  service_code=carrier.starshipit_service_code,
                                  shipping_carrier=carrier.name))

            shipping_packages, items = carrier._starshipit_get_package_information(picking=picking)
            warehouse = picking.location_id.warehouse_id
            from_partner = warehouse.partner_id
            to_partner = picking.partner_id
            if is_return:
                from_partner = picking.partner_id
                to_partner = picking.picking_type_id.warehouse_id.partner_id
            order = {
                'order_date': format_date(carrier.env, picking.date),
                'order_number': starshipit_picking_number,  # Displayed in starshipit
                'reference': picking.partner_id.display_name[:50],
                # The shipping method must match a rule in starshipit, so that the carrier will be assigned properly
                'shipping_method': carrier.starshipit_service_code,
                'return_order': is_return,
                'currency': (picking.sale_id.currency_id or picking.company_id.currency_id).name,
                'sender_details': self._populate_partner_details(from_partner),
                'destination': self._populate_partner_details(to_partner, carrier, True),
                'items': items,
                'packages': shipping_packages,
            }
            orders.append(order)

        result = self._send_request('orders/import', method='POST', data={
            'orders': orders
        })
        return {
            'success': result['success'],
            'orders': {order['order_number']: order for order in result['orders']},
        }

    @staticmethod
    def _populate_partner_details(partner, carrier=False, is_destination=False):
        Starshipit._validate_partner_fields(partner)
        details = {
            'name': partner.name,
            'email': partner.email,
            'phone': partner.phone or partner.mobile,
            'company': partner.commercial_company_name or partner.name,
            'street': partner.street,
            'city': partner.city,
            'state': partner.state_id.code,
            'post_code': partner.zip,
            'country': partner.country_id.name,
        }

        if is_destination:
            details.update({
                'delivery_instructions': carrier and carrier.carrier_description or '',
                'tax_number': partner.vat,
            })

        return details

    def _create_label(self, order_id):
        return self._send_request(
            'orders/shipment',
            method='POST',
            data={
                'order_id': order_id,
            }
        )

    def _delete_order(self, order_id):
        self._send_request(
            'orders/delete',
            method='DELETE',
            params={
                'order_id': order_id,
            }
        )

    def _archive_order(self, order_id):
        return self._send_request(
            'orders/archive',
            method='POST',
            params={
                'order_id': order_id,
            }
        )

    def _get_order_details(self, order_id):
        return self._send_request(
            'orders',
            method='GET',
            params={
                'order_id': order_id,
            })

    def _manifest_orders(self, order_ids):
        return self._send_request(
            'orders/manifest',
            method='POST',
            data={
                'order_ids': order_ids
            })

    def _get_tracking_link(self, order_number):
        return self._send_request(
            'track',
            method='GET',
            params={
                'order_number': order_number,
            }
        )

    def _get_delivery_services(self, origin_partner):
        self._validate_partner_fields(origin_partner)
        return self._send_request('deliveryservices', method='POST', data={
            'street': origin_partner.street,
            'post_code': origin_partner.zip,
            'country_code': origin_partner.country_code,
            'packages': [{}],
        })

    def _clone_order(self, order_id):
        return self._send_request('orders/shipment/clone', data={
            'order_id': order_id,
            'to_return_shipment': True,
        })

    @staticmethod
    def _validate_partner_fields(partner):
        """ Make sure that the essential fields are filled in. Other error specific to each carrier could still arise,
        but this should prevent too many errors with starshipit.
        """
        required_address_fields = ['street', 'city', 'country_id', 'state_id']
        fields_details = partner.fields_get(required_address_fields, ['string'])
        for field in required_address_fields:
            if not partner[field]:
                field_name = fields_details[field]['string']
                raise UserError(_('Please fill in the fields %s on the %s partner.', field_name, partner.name))

    @staticmethod
    def _get_starshipit_order_number(picking):
        """ Starshipit requires unique order numbers.
        In order to reduce the risk of having duplication as much as possible, we will use the company_id and the database
        uuid in order to get a unique but easily recomputable reference and add it to the picking number.
        """
        database_uuid = picking.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return f"{picking.name}#{picking.company_id.id}-{database_uuid[:5]}"
