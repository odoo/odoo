# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import re
import requests


from datetime import datetime
from markupsafe import Markup
from textwrap import shorten
from urllib.parse import urlencode, quote

from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_round
from odoo.tools import format_list

_logger = logging.getLogger(__name__)

SANDBOX_URL = "https://api-test.envia.com/"
SANDBOX_QUERY_URL = "https://queries-test.envia.com/"
SANDBOX_LABEL_URL = "https://dev.envia.com/"
PROD_URL = "https://api.envia.com/"
PROD_QUERY_URL = "https://queries.envia.com/"
PROD_LABEL_URL = "https://envia.com/"
GEOLOCATE_URL = "https://geocodes.envia.com/"

# Envia uses custom state codes for certain states different then odoo expects.
# Store a map of (country_code, state_code) to envia code.
STATE_CODE_MAP_ENVIA = {
    ('AR', 'A'): 'SA', ('AR', 'B'): 'BA', ('AR', 'C'): 'DF', ('AR', 'D'): 'SL', ('AR', 'E'): 'ER', ('AR', 'F'): 'LR',
    ('AR', 'G'): 'SE', ('AR', 'H'): 'CC', ('AR', 'J'): 'SJ', ('AR', 'K'): 'CT', ('AR', 'L'): 'LP', ('AR', 'M'): 'MZ',
    ('AR', 'N'): 'MN', ('AR', 'P'): 'FM', ('AR', 'Q'): 'NQ', ('AR', 'R'): 'RN', ('AR', 'S'): 'SF', ('AR', 'T'): 'TM',
    ('AR', 'U'): 'CH', ('AR', 'V'): 'TF', ('AR', 'W'): 'CN', ('AR', 'X'): 'CB', ('AR', 'Y'): 'JY', ('AR', 'Z'): 'SC',
    ('CA', 'YT'): 'YK', ('CL', '01'): 'TA', ('CL', '02'): 'AN', ('CL', '03'): 'AT', ('CL', '04'): 'CO', ('CL', '05'): 'VS',
    ('CL', '06'): 'LI', ('CL', '07'): 'ML', ('CL', '08'): 'BI', ('CL', '09'): 'AR', ('CL', '10'): 'LL', ('CL', '11'): 'AI',
    ('CL', '12'): 'MA', ('CL', '13'): 'RM', ('CL', '14'): 'LR', ('CL', '15'): 'AP', ('CL', '16'): 'NB', ('ES', 'ME'): 'ML',
    ('GT', 'GUA'): 'GU', ('GT', 'QUE'): 'QZ', ('IN', 'CG'): 'CT', ('IN', 'TS'): 'TG', ('IN', 'UK'): 'UT', ('MX', 'AGU'): 'AGS',
    ('MX', 'DUR'): 'DGO', ('MX', 'GUA'): 'GTO', ('MX', 'HID'): 'HGO', ('MX', 'QUE'): 'QRO', ('PE', '01'): 'AMA', ('PE', '02'): 'ANC',
    ('PE', '03'): 'APU', ('PE', '04'): 'ARE', ('PE', '05'): 'AYA', ('PE', '06'): 'CAJ', ('PE', '07'): 'CAL', ('PE', '08'): 'CUS',
    ('PE', '09'): 'HUV', ('PE', '10'): 'HUC', ('PE', '11'): 'ICA', ('PE', '12'): 'JUN', ('PE', '13'): 'LAL', ('PE', '14'): 'LAM',
    ('PE', '15'): 'LIM', ('PE', '16'): 'LOR', ('PE', '17'): 'MDD', ('PE', '18'): 'MOQ', ('PE', '19'): 'PAS', ('PE', '20'): 'PIU',
    ('PE', '21'): 'PUN', ('PE', '22'): 'SAM', ('PE', '23'): 'TAC', ('PE', '24'): 'TUM', ('PE', '25'): 'UCA'
}

ENVIA_CONTENT_LENGTH_LIMIT = 35


class Envia:
    def __init__(self, carrier, prod_environment, debug_logger):
        self.url = PROD_URL if prod_environment else SANDBOX_URL
        self.query_url = PROD_QUERY_URL if prod_environment else SANDBOX_QUERY_URL
        self.tracking_url = PROD_LABEL_URL if prod_environment else SANDBOX_LABEL_URL
        self.session = requests.Session()
        self.carrier = carrier
        self.debug_logger = debug_logger
        self.token = carrier.sudo().envia_production_api_key if prod_environment else carrier.sudo().envia_sandbox_api_key

    def _make_api_request(self, endpoint, is_query=False, geolocate=False, method='GET', data=None, params=None):
        """ Make an api call, return response for multiple api requests of Envia"""
        headers = {
            'Content-Type': "application/json; charset=utf-8",
            'Accept': "application/json",
            'Authorization': f"Bearer {self.token}"
        }

        access_url = self.url + endpoint
        if is_query:
            access_url = self.query_url + endpoint
        elif geolocate:
            access_url = GEOLOCATE_URL + endpoint
        try:
            # Envia does not handle UTF-8 Strings according to the JSON Spec properly.
            # Requests sent with escaped unicode (\\u) characters will fail on Envia's side and not
            # be able to be properly parsed. We need to encode the data with ensure_ascii set to
            # false to send the data with (\x) instead.
            if data:
                data = json.dumps(data, ensure_ascii=False).encode('utf8')

            # Log the request details for debugging purposes
            self.debug_logger("%s\n%s\n%s" % (access_url, method, data), 'envia_request_%s' % endpoint)
            # Make the API request
            response = self.session.request(method=method, url=access_url, data=data, headers=headers, params=params, timeout=30)
            # Parse the response as JSON
            response_json = response.json()
            # Log the response details for debugging purposes
            self.debug_logger("%s\n%s\n%s" % (response.url, response.status_code, response.text), 'envia_response_%s' % endpoint)
            return response_json
        except requests.exceptions.ConnectionError as error:
            _logger.warning('Connection Error: %s with the given URL: %s', error, access_url)
            return {'error': {'description': 'timeout', 'message': "Cannot reach the server. Please try again later."}}
        except requests.exceptions.ReadTimeout as error:
            _logger.warning('Timeout Error: %s with the given URL: %s', error, access_url)
            return {'error': {'description': 'timeout', 'message': "Cannot reach the server. Please try again later."}}
        except json.decoder.JSONDecodeError as error:
            _logger.warning('JSONDecodeError: %s', error)
            return {'error': {'description': 'JSONDecodeError', 'message': str(error)}}
        except Exception as error:
            _logger.warning('UnknownException: %s', error)
            return {'error': {'description': 'Exception', 'message': str(error)}}

    def _envia_parse_error(self, json_data):
        """ Return error message(s) from Envia requests formated.
        If not in debug mode, show only a smaller message.
        """
        error_msgs = []
        if message := json_data.get('message'):
            description = json_data.get('description', '')
            location = json_data.get('location', '')
            reference = json_data.get('reference', 'N/A')
            error_msgs.append(self.carrier.env._(
                "Envia Error: %(message)s - %(description)s %(location)s (Reference code: %(reference)s)",
                message=message, description=description, location=location, reference=reference
            ))

        error = json_data.get('error')
        if error and isinstance(error, dict):
            error_msgs.append(self.carrier.env._(
                "Envia Error: %(description)s - %(message)s",
                description=error['description'], message=error['message']
            ))
        return "\n".join(error_msgs)

    def _envia_format_services(self, shipper, package_type='pallet'):
        services = []
        if package_type == 'box':
            if shipper.country_id == shipper.env.ref('base.ca'):
                service_code = 'return_at_senders_expense' if self.carrier.envia_return_at_senders_expense else 'abandon'
                services.append({'data': {}, 'service': service_code})

        if package_type == 'pallet':
            if shipper.country_id in [shipper.env.ref('base.us'), shipper.env.ref('base.mx')]:
                if self.carrier.envia_lift_pickup:
                    services.append({'service': 'liftgate_pickup'})

                if self.carrier.envia_lift_delivery:
                    services.append({'service': 'liftgate_delivery'})

            if shipper.country_id == shipper.env.ref('base.us'):
                if self.carrier.envia_residential_pickup:
                    services.append({'service': 'pickup_residential_zone'})

                if self.carrier.envia_residential_delivery:
                    services.append({'service': 'delivery_residential_zone'})
        return services

    def _get_rate(self, shipper, recipient, packages_data, order):
        """ Fetch rate from Envia API based on the parameters.
        url: ship/rate
        """
        packages = []
        package_type = self.carrier.envia_default_package_type_id.envia_mail_type
        for package in packages_data:
            pack = {
                'name': 'items',
                'content': 'items',
                'amount': 1,
                'type': package_type,
                'declaredValue': package['value'],
                'insurance': package['insurance'],
                'weight': package['weight'],
                'weightUnit': 'KG',
                'lengthUnit': 'CM',
                'dimensions': package['dimensions'],
                'additionalServices': []
            }
            pack['additionalServices'].extend(self._envia_format_services(shipper, package_type))

            packages.append(pack)

        data = {
            'origin': self._prepare_address_values(shipper, is_cust=False),
            'destination': self._prepare_address_values(recipient, is_cust=True),
            'packages': packages,
            'shipment': {
                'carrier': self.carrier.envia_carrier_code,
                'service': self.carrier.envia_service_code,
                'type': 2 if package_type == 'pallet' else 1,
            },
            'settings': {
                'currency': self.carrier.envia_currency_id.name
            }
        }
        rate_json = self._make_api_request('ship/rate', method="POST", data=data)

        if not rate_json or isinstance(rate_json, dict) and rate_json.get('meta') not in ['rate', 'rateLtl']:
            # Error message found
            return {'error_found': self._envia_parse_error(rate_json)}

        services = rate_json.get('data')
        if not isinstance(services, list) or not services:
            return {'error_found': order.env._("No rate found")}

        return {
            'price': self._convert_currency(services[0].get('totalPrice'), order=order, from_envia=True)
        }

    def _rate_request(self, recipient, shipper, order, order_weight=False):
        """ Returns the dictionary of shipment rate from Envia
        url: ship/rate
        """
        if not order:
            raise UserError(order.env._("Sale Order is required to get rate."))
        products = order.order_line.product_id
        bad_products = products.filtered(lambda prod: not prod.weight and prod.type == 'consu').mapped('name')
        if bad_products:
            product_names = ",".join(bad_products)
            raise ValidationError(order.env._(
                "Envia Error: The following products don't have weights set: %(product_names)s",
                product_names=product_names
            ))

        default_package = self.carrier.envia_default_package_type_id
        packages = self.carrier._get_packages_from_order(order, default_package)

        packages_data = []
        for package in packages:
            if len(packages) == 1:
                weight = order_weight or package.weight
            else:
                weight = package.weight
            weight_in_kg = self.carrier._envia_convert_weight(weight)
            # Resize dimensions to CM
            dimensions = {
                'length': self.carrier._envia_convert_size(package.dimension['length']),
                'width': self.carrier._envia_convert_size(package.dimension['width']),
                'height': self.carrier._envia_convert_size(package.dimension['height'])
            }

            # Compute cost of package
            value = sum(comm.monetary_value * comm.qty for comm in package.commodities)
            declared_value = self._convert_currency(value, order=order, from_envia=False)
            insurance = float_round(declared_value * self.carrier.shipping_insurance / 100, 2)
            packages_data.append({
                'weight': weight_in_kg,
                'dimensions': dimensions,
                'value': declared_value,
                'insurance': insurance
            })
        return self._get_rate(shipper, recipient, packages_data, order)

    def _fetch_envia_carriers(self):
        """ Import all available carriers from Envia for specific country
        query_url: available-service/{country_code}/{international}/{shipment_type}
        """
        country_code = quote(self.carrier.country_id.code)
        ship_type = 2 if self.carrier.envia_default_package_type_id.envia_mail_type == 'pallet' else 1
        carriers = []
        for international in [0, 1]:
            carrier_json = self._make_api_request(f'available-service/{country_code}/{international}/{ship_type}', is_query=True)
            if carrier_json.get('statusCode') == 401:
                raise UserError(self.carrier.env._(
                    "Envia Error: The API key you entered for %(carrier_name)s seems to be invalid",
                    carrier_name=self.carrier.name
                ))
            carrier_data = carrier_json.get('data')
            if not carrier_data or not isinstance(carrier_data, list):
                return {'carriers': carriers, 'error': self._envia_parse_error(carrier_json)}
            carriers.extend(carrier_data)

        return {'carriers': carriers}

    def _convert_currency(self, amount, picking=False, order=False, from_envia=False):
        """ Convert the currency of an amount either to or from the envia currency
        specified on the carrier.

        Envia expects all shippings to be within the currency specified in the front end
        and as such we need to translate the picking currency one way or another.
        """
        if not (order or picking):
            raise UserError(self.carrier.env._('Sale Order or Picking is required to convert currency.'))
        envia_currency = self.carrier.envia_currency_id
        if picking:
            currency = picking.sale_id and picking.sale_id.currency_id or picking.company_id.currency_id
            company = picking.company_id or picking.env.company
            convert_date = picking.date_done or datetime.today()
        else:
            currency = order.currency_id or order.company_id.currency_id
            company = order.company_id or order.env.company
            convert_date = datetime.today()

        source_currency = envia_currency if from_envia else currency
        dest_currency = currency if from_envia else envia_currency

        if dest_currency.id != source_currency.id:
            return source_currency._convert(amount, dest_currency, company, convert_date)
        return amount

    def _get_shipping_lines(self, package):
        """ Returns the shipping products from the specific
        picking to create the order.
        """
        line_by_product = []
        original_prices = []
        picking = package.picking_id

        for commodity in package.commodities:
            unit_price = round(commodity.monetary_value, 2)
            # Price of the item must be in the currency you created your Envia account with
            unit_price_in_currency = self._convert_currency(unit_price, picking=picking, from_envia=False)
            item = {
                'description': shorten(commodity.product_id.name, ENVIA_CONTENT_LENGTH_LIMIT, placeholder="..."),
                'quantity': commodity.qty,
                'price': unit_price_in_currency,
            }
            if commodity.product_id.hs_code:
                # Pass international information if it's necessary
                item |= {
                    'productCode': commodity.product_id.hs_code.replace('.', '') or '',
                    'countryOfManufacture': commodity.country_of_origin or ''
                }
            line_by_product.append(item)
            # Store the original currency price so we don't lose rounding precision for declaredValue
            original_prices.append(unit_price * commodity.qty)

        return line_by_product, original_prices

    def _prepare_parcel(self, package, origin):
        """ Prepare parcel for picking shipment based on the package.
        Use the origin partner to see if we need to add Mexico specific
        code.
        """
        dimensions = package.dimension
        # Resize dimensions to CM
        for dim, size in dimensions.items():
            dimensions[dim] = self.carrier._envia_convert_size(size)

        net_weight_in_kg = self.carrier._envia_convert_weight(package.weight)
        package_type = package.packaging_type

        picking = package.picking_id

        items, original_prices = self._get_shipping_lines(package)
        contents = ", ".join(commodity.product_id.name for commodity in package.commodities)

        # Envia limits to 35 characters, if it's too long use categories instead.
        if len(contents) > ENVIA_CONTENT_LENGTH_LIMIT:
            categories = [comm.product_id.categ_id.name for comm in package.commodities]
            contents = shorten(", ".join(categories), ENVIA_CONTENT_LENGTH_LIMIT, placeholder="...")
        # Store the total price of all items in this package as a insurance value
        sum_price = sum(original_prices)
        declared_value = self._convert_currency(sum_price, picking=picking, from_envia=False)
        insurance_value = float_round(declared_value * self.carrier.shipping_insurance / 100, 2)
        parcel = {
            'type': package_type,
            'name': package.name,
            'content': contents,
            'amount': 1,
            'insurance': insurance_value,
            'declaredValue': declared_value,
            'lengthUnit': "CM",
            'weightUnit': "KG",
            'weight': net_weight_in_kg,
            'dimensions': dimensions,
            'additionalServices': []
        }

        parcel['additionalServices'].extend(self._envia_format_services(origin, package_type))

        if package_type == 'box':
            parcel['items'] = items

        if package_type == 'pallet':
            if origin.country_id == origin.env.ref('base.mx'):
                # Envia requires an extra field to be set for mexico when sending parcels/ltl shipments.
                # It requires the unspsc_code which is in product_unspsc module, however this is only for
                # orders shipped from mexico which requires the localization installed which depends on unspsc.
                complementData = []
                product_unspsc = origin.env['ir.module.module'].search([('name', '=', 'product_unspsc')])
                for comm in package.commodities:
                    unspsc = product_unspsc.state == 'installed' and comm.product_id.unspsc_code_id
                    if not unspsc:
                        msg = origin.env._("For LTL shipments in Mexico, a Bill of Landing (Carta Porte) is required, "
                                "in order to send the required information you need to set the UNSPSC code in "
                                "the following product: %(product_name)s", product_name=comm.product_id.display_name)
                        raise ValidationError(msg)
                    complementData.append({
                        'productCode': unspsc.code,
                        'productDescription': shorten(unspsc.name, ENVIA_CONTENT_LENGTH_LIMIT, placeholder="..."),
                        'weightUnit': "X8A",
                        'quantity': comm.qty,
                        'unitPrice': round(comm.monetary_value, 2),
                        'currency': self.carrier.envia_currency_id.name
                    })
                parcel['bolComplement'] = complementData

        return parcel

    def _get_shipping_params(self, picking):
        """ Returns the shipping data from picking for create a Envia Order."""
        envia_carrier = self.carrier.envia_carrier_code
        envia_service = self.carrier.envia_service_code

        picking_data = {}
        ship_from = picking.picking_type_id.warehouse_id.partner_id or picking.warehouse_id.company_id.partner_id

        bad_products = picking.move_line_ids.product_id.filtered(lambda prod: not prod.weight and prod.type == 'consu').mapped('name')
        if bad_products:
            product_names = ",".join(bad_products)
            raise ValidationError(picking.env._(
                "Envia Error: The following products don't have weights set: %(product_names)s",
                product_names=product_names
            ))

        default_package = self.carrier.envia_default_package_type_id
        packages = self.carrier._get_packages_from_picking(picking, default_package)
        package_types = packages and {package.packaging_type for package in packages}

        if not package_types or any(package_type != default_package.envia_mail_type for package_type in package_types):
            # The carrier/service selected on the delivery carrier model only works. If the package
            # is of the same type as the default_packages' type. They need to use the right type.
            raise ValidationError(picking.env._(
                "Envia Error: The Envia Mail Type (%(package_types)s) set on the package(s) does "
                "not match the type set on the carrier (%(carrier_package_type)s). "
                "Use a different package or different carrier that matches the mail type.",
                package_types=package_types, carrier_package_type=default_package.envia_mail_type
            ))


        picking_data = {
            'origin': self._prepare_address_values(ship_from, is_cust=False),
            'destination': self._prepare_address_values(picking.partner_id, is_cust=True),
            'packages': [],
            'settings': {
                'printFormat': self.carrier.envia_label_file_type,
                'printSize': self.carrier.envia_label_stock_type,
            },
            'shipment': {
                'carrier': envia_carrier,
                'service': envia_service,
                'type': 2 if default_package.envia_mail_type == 'pallet' else 1,
            },
        }
        for package in packages:
            picking_data['packages'].append(self._prepare_parcel(package, origin=ship_from))

        return picking_data

    def _send_shipping(self, picking):
        """ Returns a dictionary containing:
            - Price of the shipment
            - All tracking numbers for each package
            - Envia Order Ids for cancelation.
        url(s): ship/generate
        """
        res = {
            'exact_price': 0.00,
            'tracking_number': '',
        }
        picking_data = self._get_shipping_params(picking)

        ship_response = self._make_api_request('ship/generate', method='POST', data=picking_data)
        if not ship_response or isinstance(ship_response, dict) and ship_response.get('meta') not in ['generate', 'generateLtl']:
            # Error message found
            raise UserError(self._envia_parse_error(ship_response))

        data_list = ship_response.get('data')
        tracking_numbers = []
        label_urls = []
        additional_files = []

        for order_data in data_list:
            tracking_numbers.append(order_data.get('trackingNumber'))
            label_urls.append(order_data.get('label'))
            additional_files += order_data.get('additionalFiles')

        params = {
            'label': ','.join(tracking_numbers)
        }
        tracking_url = self.tracking_url + f"tracking?{urlencode(params)}"
        formatted_tracking = format_list(picking.env, tracking_numbers)

        carrier_tracking_link = Markup("<a href='%s'>%s</a><br/>") % (tracking_url, formatted_tracking)

        # pickings where we should leave a lognote
        lognote_pickings = picking.sale_id.picking_ids if picking.sale_id else picking

        logmessage = Markup(
            "{header}<br/><b>{tracking_header}</b> {tracking_link}<br/>"
        ).format(
            header=picking.env._("Shipment created into Envia"),
            tracking_header=picking.env._("Tracking Numbers:"),
            tracking_link=carrier_tracking_link
        )
        label_data = []
        for label_url, track_number in zip(label_urls, tracking_numbers):
            try:
                response = self.session.get(url=label_url, timeout=30)
                response.raise_for_status()
                label_data.append(('%s-%s.%s' % (self.carrier._get_delivery_label_prefix(), track_number, self.carrier.envia_label_file_type), response.content))
            except (requests.exceptions.HTTPError, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                logmessage += Markup('<li><a href="%s">%s</a></li>') % (label_url, label_url)

        for pick in lognote_pickings:
            pick.message_post(body=logmessage, attachments=label_data)

        if additional_files:
            logmessage = Markup("{header}<br/>").format(header=picking.env._("Envia Documents:"))
            forms_data = []
            for form_url in additional_files:
                try:
                    response = self.session.get(form_url, timeout=30)
                    response.raise_for_status()
                    forms_data.append(('%s-%s' % (self.carrier._get_delivery_doc_prefix(), form_url.split('/')[-1]), response.content))
                except (requests.exceptions.HTTPError, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                    logmessage += Markup('<li><a href="%s">%s</a></li>') % (form_url, form_url)
            for pick in lognote_pickings:
                pick.message_post(body=logmessage, attachments=forms_data)

        price = sum(order.get('totalPrice') for order in data_list)
        res['exact_price'] = self._convert_currency(price, picking=picking, from_envia=True)
        res['tracking_number'] = ','.join(tracking_numbers)
        return res

    def _cancel_picking(self, picking):
        """ Cancel the individual order
        Can end up failing still even if we check that it can be canceled.
        Returns a list of any tracking that failed to cancel.
        url: ship/cancel/
        """
        carrier = self.carrier.envia_carrier_code
        tracking_numbers = picking.carrier_tracking_ref

        invalid_trackings = []
        for tracking_number in tracking_numbers.split(','):
            body = {
                'carrier': carrier,
                'trackingNumber': tracking_number
            }

            cancel_response = self._make_api_request('ship/cancel', method='POST', data=body)
            if isinstance(cancel_response, dict) and cancel_response.get('meta') != 'cancel':
                invalid_trackings.append(tracking_number)
        return invalid_trackings

    def _get_envia_state_code(self, partner):
        """ Envia requires the state code to be sent for the partner,
        however, the codes they use are slightly different then
        the ISO codes we store in Odoo. If we don't have a special
        code we fall back on the default state code.
        """
        envia_state_code = STATE_CODE_MAP_ENVIA.get((partner.country_id.code, partner.state_id.code))
        return envia_state_code or partner.state_id.code

    def _get_envia_vat(self, partner):
        """ Envia requires the vat of the partner.
        If the partner is a delivery address then the vat is on the parent_id

        In colombia, Envia doesn't expect any periods or - in the vat even
        though we store it so we must strip it.
        """
        vat = partner.parent_id.vat if partner.type != 'contact' else partner.vat
        if vat and partner.country_id == partner.env.ref("base.co"):
            vat = vat.split("-", 1)[0]
            vat = re.sub("[^+0-9]", "", vat)
        return vat

    def _get_envia_city(self, partner):
        city = partner.city_id.name or partner.city
        return city

    def _get_envia_street(self, partner):
        street = partner.street_name or partner.street
        return street

    def _get_envia_district(self, partner):
        """ Envia requires the city to be sent twice for chile.
        Skip district code and do that instead.

        For Mexico envia requires the colony field if it's set and
        l10n_mx_edi_extended is installed.
        """
        if partner.country_id == partner.env.ref("base.cl"):
            return self._get_envia_city(partner)

        l10n_mx = partner.env['ir.module.module'].search([('name', '=', 'l10n_mx_edi_extended')])
        if l10n_mx.state == 'installed' and partner.l10n_mx_edi_colony:
            return partner.l10n_mx_edi_colony

        district = partner.street2
        return district

    def _geolocate_zip(self, partner):
        """ In some countries the idea of a zipcode/pincode is not something
        that is required in envia's front-end. However, they expect specific codes
        that may be not filled in the partner form or slightly different.
        If it's not set on the partner we try and geo-locate it before throwing
        an error.

        url: locate/{country_code}/{state_code}/{city_name}
        """
        if not (partner.country_id and (partner.city_id or partner.city) and partner.state_id):
            return False
        country_code = quote(partner.country_id.code)
        city_name = quote(self._get_envia_city(partner))
        state_code = quote(self._get_envia_state_code(partner))

        geolocate_data = self._make_api_request(f'locate/{country_code}/{state_code}/{city_name}', geolocate=True)
        if not geolocate_data or isinstance(geolocate_data, dict):
            return False

        geolocate_data = geolocate_data[0]

        zip_data = geolocate_data.get('zip_codes', [])
        if not zip_data:
            return False
        return zip_data[0].get('zip_code')

    def _get_envia_zip(self, partner):
        # l10n_co_edi module stores the state code for colombia
        # If that module is installed on the db we can shortcut the api call
        # and return the value immediately.
        l10n_co = partner.env['ir.module.module'].search([('name', '=', 'l10n_co_edi')])

        if l10n_co.state == 'installed' and partner.city_id.l10n_co_edi_code:
            base_code = str(partner.city_id.l10n_co_edi_code)
            return base_code

        if not (partner.zip or partner.city_id.zipcode):
            zipcode = self._geolocate_zip(partner)
            if not zipcode:
                msg = partner.env._(
                    "Envia was unable to locate a postal code for the partner: %(partner_name)s. "
                    "Make sure city/commune and state/region are set otherwise enter a postal code directly",
                    partner_name=partner.display_name
                )
                raise ValidationError(msg)
            return zipcode
        return partner.zip or partner.city_id.zipcode

    def _get_envia_phone(self, partner):
        """ Envia requires all phone numbers to be in national format
        (Even for international shipments)
        """
        phone = partner.phone or partner.mobile
        phone: str = partner._phone_format(number=phone, force_format='NATIONAL') or phone
        if phone:
            # Clean phonenumber of non numeric digits.
            phone = re.sub("[^+0-9]", "", phone)[:20]

        if not phone:
            msg = partner.env._("A phone number must be set on Partner: %(partner_name)s", partner_name=partner.display_name)
            raise ValidationError(msg)
        return phone

    def _prepare_address_values(self, partner, is_cust=False):
        """ Try and prepare the address dictionary required for origin/destination.
        Throw Validation error if it fails.
        Each country has a different set of required fields, we pull the information
        from Envia and then use a mapping of their field names to ours. Some of their
        requirements are more specific than one field on the model so we need functions
        to perform the data validation/computation.

        url: generic-form?country_code={country_code}&form=address_info

        """
        c_code = partner.country_id.code
        params = {
            'country_code': c_code,
            'form': 'address_info'
        }
        country_requirements = self._make_api_request('generic-form', is_query=True, params=params)
        if isinstance(country_requirements, dict) and any(field in country_requirements for field in ['error', 'errors', 'message']):
            raise ValidationError(self._envia_parse_error(country_requirements))

        # Map Envia address keys to functions that take in the partner and return the correct data.
        field_map = {
            'district': self._get_envia_district,
            'state': self._get_envia_state_code,
            'city': self._get_envia_city,
            'identificationNumber': self._get_envia_vat,
            'city_select': self._get_envia_city,
            'postalCode': self._get_envia_zip,
            'phone': self._get_envia_phone,
            'street': self._get_envia_street,
        }
        missing_fields = []
        address_dict = {
            'name': partner.name,
            'country': partner.country_id.code,
            'company': partner.commercial_company_name or '',
            'number': partner.street_number or partner.street2 or '',
            'street': self._get_envia_street(partner),
            'email': partner.email,
            'phone': self._get_envia_phone(partner),
            'type': 'destination' if is_cust else 'origin'
        }

        for field in country_requirements:
            envia_name = field.get('fieldId')
            envia_label = field.get('fieldName')
            rules = field.get('rules', {})
            required = rules.get('required', False)

            key = envia_name if envia_name in field_map else envia_label
            # Skip pre-populated fields
            if address_dict.get(key) or key not in field_map:
                continue

            envia_func = field_map[key]
            value = envia_func(partner)
            if value:
                address_dict[key] = value
            elif required:
                # Only complain if it's a required field.
                missing_fields.append(partner.env._(
                    '%(field_name)s must be set on Partner: %(partner_name)s.',
                    field_name=envia_name,
                    partner_name=partner.display_name
                ))

        if missing_fields:
            msg = "\n".join(missing_fields)
            raise ValidationError(partner.env._('Missing Fields:\n%s', msg))

        if partner.country_id == partner.env.ref('base.co'):
            # Colombia requires their city field to be the postal code not the city name.
            zipcode = address_dict['postalCode'].rjust(5, '0').ljust(8, '0')
            address_dict['city'] = address_dict['postalCode'] = zipcode

        return address_dict
