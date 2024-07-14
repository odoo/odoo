# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import requests
import re
from werkzeug.urls import url_join

from odoo import _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_is_zero, float_repr

API_BASE_URL = 'https://api.easypost.com/v2/'
NON_BLOCKING_MESSAGES = ['rate_message']

class EasypostRequest():
    "Implementation of Easypost API"

    def __init__(self, api_key, debug_logger):
        self.api_key = api_key
        self.debug_logger = debug_logger
        self.is_domestic_shipping = None

    def _make_api_request(self, endpoint, request_type='get', data=None):
        """make an api call, return response"""
        access_url = url_join(API_BASE_URL, endpoint)
        try:
            self.debug_logger("%s\n%s\n%s" % (access_url, request_type, data if data else None), 'easypost_request_%s' % endpoint)
            if request_type == 'get':
                response = requests.get(access_url, auth=(self.api_key, ''), data=data)
            else:
                response = requests.post(access_url, auth=(self.api_key, ''), data=data)
            self.debug_logger("%s\n%s" % (response.status_code, response.text), 'easypost_response_%s' % endpoint)
            response = response.json()
            # check for any error in response
            if 'error' in response:
                error_message = response['error'].get('message')
                error_detail = response['error'].get('errors')
                if error_detail:
                    error_message += ''.join(['\n - %s: %s' % (err.get('field', _('Unspecified field')), err.get('message', _('Unknown error'))) for err in error_detail])
                raise UserError(_('Easypost returned an error: %s', error_message))
            return response
        except Exception as e:
            raise e

    def fetch_easypost_carrier(self):
        """ Import all carrier account from easypost
        https://www.easypost.com/docs/api.html#carrier-accounts
        It returns a dict with carrier account name and it's
        easypost id in order to generate shipments.
        e.g: {'FeDex: ca_27839172aee03918a701'}
        """
        carriers = self._make_api_request('carrier_accounts')
        carriers = {c['readable']: c['id'] for c in carriers}
        if carriers:
            return carriers
        else:
            # The user need at least one carrier on its easypost account.
            # https://www.easypost.com/account/carriers
            raise UserError(_("You have no carrier linked to your Easypost Account.\
                Please connect to Easypost, link your account to carriers and then retry."))

    def fetch_easypost_user(self):
        """ Import data about the current user
        https://www.easypost.com/docs/api/curl#retrieve-a-user
        It returns a dict of info regarding the current user,
        such as its `id` or his related `insurance_fee_rate`.
        """
        return self._make_api_request('users')

    def _check_required_value(self, carrier, recipient, shipper, order=False, picking=False):
        """ Check if the required value are present in order
        to process an API call.
        return True or an error if a value is missing.
        """
        # check carrier credentials
        if carrier.prod_environment and not carrier.sudo().easypost_production_api_key:
            raise UserError(_("The %s carrier is missing (Missing field(s) :\n Production API Key)", carrier.name))
        elif not carrier.sudo().easypost_test_api_key:
            raise UserError(_("The %s carrier is missing (Missing field(s) :\n Test API Key)", carrier.name))

        if not carrier.easypost_delivery_type:
            raise UserError(_("The %s carrier is missing (Missing field(s) :\n Delivery Carrier Type)", carrier.name))

        if not carrier.easypost_default_package_type_id:
            raise UserError(_("The %s carrier is missing (Missing field(s) :\n Default Package Type)", carrier.name))

        if not order and not picking:
            raise UserError(_("Sale Order/Stock Picking is missing."))

        # check required value for order
        if order:
            if not order.order_line:
                raise UserError(_("Please provide at least one item to ship."))
            error_lines = order.order_line.filtered(lambda line: not line.product_id.weight and line.product_qty != 0 and not line.is_delivery and line.product_id.type != 'service' and not line.display_type)
            if error_lines:
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s", ", ".join(error_lines.product_id.mapped('name')))

        # check required value for picking
        if picking:
            if not picking.move_ids:
                raise UserError(_("Please provide at least one item to ship."))
            if picking.move_ids.filtered(lambda line: not line.weight and line.product_qty != 0):
                raise UserError(_('The estimated price cannot be computed because the weight of your product is missing.'))
        return True

    def _prepare_address(self, addr_type, addr_obj):
        """ Create a dictionary with list of available
        value to easypost.
        param string: addr_type: 'from_address' for shipper
        or 'to_address' for recipient.
        param addr_obj res.partner: partner linked to order/picking
        in order to retrieve shipping information
        return str: response address id of API request to create an address.
        We do an extra API request since the address creation is free of charge.
        If there is an error about address it will be raise before the rate
        or shipment request.
        """
        addr_fields = {
            'street1': 'street', 'street2': 'street2',
            'city': 'city', 'zip': 'zip', 'phone': 'phone',
            'email': 'email'}
        address = {'order[%s][%s]' % (addr_type, field_name): addr_obj[addr_obj_field]
                   for field_name, addr_obj_field in addr_fields.items()
                   if addr_obj[addr_obj_field]}
        address['order[%s][name]' % addr_type] = (addr_obj.name or addr_obj.display_name)[:25]
        if addr_obj.state_id:
            address['order[%s][state]' % addr_type] = addr_obj.state_id.code
        address['order[%s][country]' % addr_type] = addr_obj.country_id.code
        if addr_obj.commercial_company_name:
            address['order[%s][company]' % addr_type] = addr_obj.commercial_company_name[:25]
        return address

    def _prepare_shipments(self, carrier, packages, is_return=False):
        """ Prepare easypost order's shipments with the real
        value used in the picking.
        It will iterates over multiple packages if they are used.
        It returns a dict with the necessary shipments (containing
        parcel/customs info used for each stock.move.line result package.
        Move lines without package are considered to be lock together
        in a single package.
        """
        shipment = {}
        for shp_id, pkg in enumerate(packages):
            shipment.update(self._prepare_parcel(carrier, shp_id, pkg, carrier.easypost_label_file_type))
            shipment.update(self._customs_info(carrier, shp_id, pkg.commodities, pkg.currency_id))
            shipment.update(self._options(shp_id, carrier))
        if is_return:
            shipment.update({'order[is_return]': True})
        return shipment

    def _prepare_parcel(self, carrier, shipment_id, delivery_package, label_format='pdf'):
        """ Prepare parcel for used package. (carrier default if it comes from
        an order). https://www.easypost.com/docs/api.html#parcels
        params:
        - Shipment_id int: The current easypost shipement.
        - delivery_package: custom 'DeliveryPackage' -> used package for shipement.
        - Weight float(oz): Product's weight contained in package
        - label_format str: Format for label to print.
        return dict: a dict with necessary keys in order to create
        a easypost parcel for the easypost shipement with shipment_id
        """
        shipment = {
            'order[shipments][%d][parcel][weight]' % shipment_id: carrier._easypost_convert_weight(delivery_package.weight),
            'order[shipments][%d][options][label_format]' % shipment_id: label_format,
            'order[shipments][%d][options][label_date]' % shipment_id: datetime.datetime.now().isoformat()
        }
        # If this is not an EasyPost predefined package, then we give the dimensions.
        packages = carrier._easypost_get_services_and_package_types()[0]
        if delivery_package.packaging_type and any(delivery_package.packaging_type in pkg_names for pkg_names in packages.values()):
            shipment.update({
                'order[shipments][%d][parcel][predefined_package]' % shipment_id: delivery_package.packaging_type
            })
        elif all(dim > 0 for dim in delivery_package.dimension.values()):
            shipment.update({
                'order[shipments][%d][parcel][%s]' % (shipment_id, dim): delivery_package.dimension[dim]
                for dim in 'height width length'.split()
            })
        else:
            raise UserError(_('Package type used in pack %s is not configured for easypost.', delivery_package.name))
        return shipment

    def _customs_info(self, carrier, shipment_id, commodities, currency):
        """ generate a dict with customs info for each package.
        https://www.easypost.com/customs-guide.html
        Currently general customs info for all packages are not generate.
        For each shipment add a customs items by move line containing
        - Product description (care it crash if bracket are used)
        - Quantity for this product in the current package
        - Total Value (unit value * qty)
        - Total Value currency
        - Total weight in ounces.
        - Original country code(warehouse)
        """
        # Customs information should be given only for international deliveries
        if self.is_domestic_shipping:
            return {}

        customs_info = {}
        contents_explanation = ', '.join(["%s" % (re.sub(r'[\W_]+', ' ', commodity.product_id.name or '')) for commodity in commodities])[:255]
        customs_info.update({'order[shipments][%d][customs_info][contents_explanation]' % (shipment_id) : contents_explanation})
        for customs_item_id, commodity in enumerate(commodities):
            customs_info.update({
                'order[shipments][%d][customs_info][customs_items][%d][description]' % (shipment_id, customs_item_id): commodity.product_id.name,
                'order[shipments][%d][customs_info][customs_items][%d][quantity]' % (shipment_id, customs_item_id): commodity.qty,
                'order[shipments][%d][customs_info][customs_items][%d][value]' % (shipment_id, customs_item_id): commodity.monetary_value * commodity.qty,
                'order[shipments][%d][customs_info][customs_items][%d][currency]' % (shipment_id, customs_item_id): currency.name,
                'order[shipments][%d][customs_info][customs_items][%d][weight]' % (shipment_id, customs_item_id): carrier._easypost_convert_weight(commodity.product_id.weight * commodity.qty),
                'order[shipments][%d][customs_info][customs_items][%d][origin_country]' % (shipment_id, customs_item_id): commodity.country_of_origin,
                'order[shipments][%d][customs_info][customs_items][%d][hs_tariff_number]' % (shipment_id, customs_item_id): commodity.product_id.hs_code,
            })
        return customs_info

    def _options(self, shipment_id, carrier):
        options = {}
        if carrier.easypost_default_service_id:
            service_otpions = carrier.easypost_default_service_id._get_service_specific_options()
            for option_name, option_value in service_otpions.items():
                options['order[shipments][%d][options][%s]' % (shipment_id, option_name)] = option_value
        return options

    def rate_request(self, carrier, recipient, shipper, order=False, picking=False, is_return=False):
        """ Create an easypost order in order to proccess
        all package at once.
        https://www.easypost.com/docs/api.html#orders
        It will process in this order:
        - recipient address (check _prepare_address for more info)
        - shipper address (check _prepare_address for more info)
        - prepare shipments (with parcel/customs info)
        - Do the API request
        If a service level is defined on the delivery carrier it will
        returns the rate for this service or an error if there is no
        rate for this service.
        If there is no service level on the delivery carrier, it will
        return the cheapest rate. this behavior could be override with
        the method _sort_rates.
        return
        - an error if rates couldn't be found.
        - API response with potential warning messages.
        """
        self._check_required_value(carrier, recipient, shipper, order=order, picking=picking)

        # Dict that will contains data in
        # order to create an easypost object
        order_payload = {}

        # reference field to track Odoo customers that use easypost for postage/shipping.
        order_payload['order[reference]'] = 'odoo'

        # Add current carrier type
        order_payload['order[carrier_accounts][id]'] = carrier.easypost_delivery_type_id

        # Add addresses (recipient and shipper)
        order_payload.update(self._prepare_address('to_address', recipient))
        order_payload.update(self._prepare_address('from_address', shipper))
        if carrier.easypost_default_service_id._require_residential_address():
            order_payload['order[to_address][residential]'] = True

        # The request differ depending on if it is a domestic shipping or an international one
        self.is_domestic_shipping = order_payload["order[from_address][country]"] == order_payload["order[to_address][country]"]

        # if picking then count total_weight of picking move lines, else count on order
        # easypost always takes weight in ounces(oz)
        if picking:
            delivery_packages = carrier._get_packages_from_picking(picking, carrier.easypost_default_package_type_id)
        else:
            delivery_packages = carrier._get_packages_from_order(order, carrier.easypost_default_package_type_id)
        order_payload.update(self._prepare_shipments(carrier, delivery_packages, is_return=is_return))

        insured_amount = 0.0
        if carrier.shipping_insurance:
            for pkg in delivery_packages:
                insured_amount += carrier._easypost_usd_insured_value(pkg.total_cost, pkg.currency_id)
        insurance_cost = 0
        if insured_amount:
            insurance_cost = carrier._easypost_usd_estimated_insurance_cost(insured_amount)

        # request for rate
        response = self._make_api_request("orders", "post", data=order_payload)
        error_message = False
        warning_message = False
        rate = False

        # explicitly check response for any messages
        # error message are catch during _make_api_request method
        if response.get('messages'):
            warning_message = ('\n'.join([x['carrier'] + ': ' + x['type'] + ' -- ' + x['message'] for x in response['messages']]))
            response.update({'warning_message': warning_message})

        # check response contains rate for particular service
        rates = response.get('rates')
        # When easypost returns a JSON without rates in probably
        # means that some data are missing or inconsistent.
        # However instead of returning a correct error message,
        # it will return an empty JSON or a message asking to contact
        # their support. In this case a good practice would be to check
        # the order_payload sent and try to find missing or erroneous value.
        # DON'T FORGET DEBUG MODE ON DELIVERY CARRIER.
        if not rates:
            error_message = _("It seems Easypost do not provide shipments for this order.\
                We advise you to try with another package type or service level.")
        elif rates and not carrier.easypost_default_service_id:
            # Get cheapest rate.
            rate = self._sort_rates(rates)[0]
            # Complete service level on the delivery carrier.
            carrier._generate_services(rates)
        # If the user ask for a specific service level on its carrier.
        elif rates and carrier.easypost_default_service_id:
            rate = [rate for rate in rates if rate['service'] == carrier.easypost_default_service_id.name]
            if not rate:
                error_message = _("There is no rate available for the selected service level for one of your package. Please choose another service level.")
            else:
                rate = rate[0]

        # warning_message could contains useful information
        # in order to correct the delivery carrier or SO/picking.
        if error_message and warning_message:
            error_message += warning_message

        response.update({
            'error_message': error_message,
            'rate': rate,
            'insurance_cost': insurance_cost,
            'insured_amount': insured_amount,
            'shipment_ids': [shipment['id'] for shipment in response.get('shipments', [])],
        })

        return response

    def send_shipping(self, carrier, recipient, shipper, picking, is_return=False):
        """ In order to ship an easypost order:
        - prepare an order by asking a rate request with correct parcel
        and customs info.
        https://www.easypost.com/docs/api.html#create-an-order
        - then buy the order with selected provider and service level.
        https://www.easypost.com/docs/api.html#buy-an-order
        - collect label and tracking data from the order buy request's
        response.
        return a dict with:
        - order data
        - selected rate
        - tracking label
        - tracking URL
        """
        # create an order
        result = self.rate_request(carrier, recipient, shipper, picking=picking, is_return=is_return)
        # check for error in result
        if result.get('error_message'):
            return result

        # buy an order
        buy_order_payload = {}
        buy_order_payload['carrier'] = result['rate']['carrier']
        buy_order_payload['service'] = result['rate']['service']
        endpoint = "orders/%s/buy" % result['id']
        response = self._make_api_request(endpoint, 'post', data=buy_order_payload)
        response = self._post_process_ship_response(response, carrier=carrier, picking=picking)
        # explicitly check response for any messages
        messages = response.get('messages', [])
        message_type = messages[0].get('type') if messages else None
        if message_type and message_type not in NON_BLOCKING_MESSAGES:
            raise UserError('\n'.join([x['carrier'] + ': ' + x['type'] + ' -- ' + x['message'] for x in response['messages']]))

        # get tracking code and lable file url
        result['track_shipments_url'] = {res['tracking_code']: res['tracker']['public_url'] for res in response['shipments'] if res['tracker']}
        result['track_label_data'] = {res['tracking_code']: res['postage_label']['label_url'] for res in response['shipments'] if res['postage_label']}

        # get commercial invoice + other forms
        result['forms'] = {form['form_type']: form['form_url'] for res in response['shipments'] for form in res.get('forms', [])}

        # buy insurance after successful order purchase
        for shp_id in result.get('shipment_ids'):
            insured_amount = result.get('insured_amount')
            if not float_is_zero(insured_amount, precision_rounding=2):
                endpoint = "shipments/%s/insure" % shp_id
                response = self._make_api_request(endpoint, 'post', data={'amount': insured_amount})
        return result

    def get_tracking_link(self, order_id):
        """ Retrieve the information on the order with id 'order_id'.
        https://www.easypost.com/docs/api.html#retrieve-an-order
        Return data relative to tracker.
        """
        tracking_public_urls = []
        endpoint = "orders/%s" % order_id
        response = self._make_api_request(endpoint)
        for shipment in response.get('shipments'):
            tracking_public_urls.append([shipment['tracking_code'], shipment['tracker']['public_url']])
        return tracking_public_urls

    def get_tracking_link_from_code(self, code):
        """ Retrieve the information from the tracking code entered manually.
        https://www.easypost.com/docs/api#retrieve-a-list-of-trackers
        Return data relative to tracker.
        """
        tracking_public_urls = []
        endpoint = "trackers"
        response = self._make_api_request(endpoint, 'get', data={'tracking_code': code})
        for tracker in response.get('trackers'):
            tracking_public_urls.append([tracker['tracking_code'], tracker['public_url']])
        return tracking_public_urls

    def _sort_rates(self, rates):
        """ Sort rates by price. This function
        can be override in order to modify the default
        rate behavior.
        """
        return sorted(rates, key=lambda rate: float(rate.get('rate')))

    def _post_process_ship_response(self, response, carrier=False, picking=False):
        """ Easypost manage different carriers however they don't follow a
        standard flow and some carriers could act a specific way compare to
        other. The purpose of this method is to catch problematic behavior and
        modify the returned response in order to make it standard compare to
        other carrier.
        """
        # With multiples shipments, some carrier will return a message explaining that
        # the rates are on the first shipments and not on the next ones.
        if response.get('messages') and carrier.easypost_delivery_type in ['Purolator', 'DPD UK', 'UPS'] and \
                len(response.get('shipments', [])) > 1 and \
                len(response.get('shipments')[0].get('rates', [])) > 0 and \
                all(len(s.get('rates', [])) == 0 for s in response['shipments'][1:]):
            if carrier.easypost_delivery_type == 'UPS' and not all(s.get('messages') for s in response['shipments'][1:]):
                # UPS also send a message on following shipments explaining that their rates is in the
                # first shipment (other carrier just return an empty list).
                return response
            if carrier.easypost_delivery_type in ['Purolator', 'DPD UK'] and (
                    len(response['messages']) != 1 or
                    response['messages'][0].get('type', '') != 'rate_error' or
                    "multi-shipment rate includes this shipment." not in response['messages'][0].get('message', '')):
                # Purolator & DPD UK send a rate_error message for this situation.
                return response

            if picking:
                picking.message_post(body=response.get('messages'))
            response['messages'] = False
        return response
