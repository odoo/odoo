# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from json import JSONDecodeError

import re

import requests
from requests import RequestException

from odoo import _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_repr, remove_accents

TEST_BASE_URL = "https://apis-sandbox.fedex.com"
PROD_BASE_URL = "https://apis.fedex.com"

# Why using standardized ISO codes? It's way more fun to use made up codes...
# https://developer.fedex.com/api/en-us/guides/api-reference.html#currencycodes
FEDEX_CURR_MATCH = {
    'XCD': 'ECD',
    'MXN': 'NMP',
    'KYD': 'CID',
    'CHF': 'SFR',
    'DOP': 'RDD',
    'JPY': 'JYE',
    'KRW': 'WON',
    'SGD': 'SID',
    'CLP': 'CHP',
    'JMD': 'JAD',
    'KWD': 'KUD',
    'AED': 'DHS',
    'TWD': 'NTD',
    'ARS': 'ARN',
    'VES': 'VEF',
    # 'LVL': 'EUR',
    # 'UYU': 'UYP',
    'GBP': 'UKL',
    # 'IDR': 'RPA',
}

FEDEX_MX_STATE_MATCH = {
    'AGU': 'AG',
    'BCN': 'BC',
    'BCS': 'BS',
    'CAM': 'CM',
    'CHH': 'CH',
    'CHP': 'CS',
    'CMX': 'DF',
    'COA': 'CO',
    'COL': 'CL',
    'DUR': 'DG',
    'GRO': 'GR',
    'GUA': 'GT',
    'HID': 'HG',
    'JAL': 'JA',
    'MEX': 'EM',
    'MIC': 'MI',
    'MOR': 'MO',
    'NAY': 'NA',
    'NLE': 'NL',
    'OAX': 'OA',
    'PUE': 'PU',
    'QUE': 'QE',
    'ROO': 'QR',
    'SIN': 'SI',
    'SLP': 'SL',
    'SON': 'SO',
    'TAB': 'TB',
    'TAM': 'TM',
    'TLA': 'TL',
    'VER': 'VE',
    'YUC': 'YU',
    'ZAC': 'ZA'
}

FEDEX_AE_STATE_MATCH = {
    'AZ': 'AB',
    'AJ': 'AJ',
    'DU': 'DU',
    'FU': 'FU',
    'RK': 'RA',
    'SH': 'SH',
    'UQ': 'UM',
}

FEDEX_STOCK_TYPE_MATCH = {
    'PAPER_4X6.75': 'PAPER_4X675',
    'PAPER_7X4.75': 'PAPER_7X475',
    'PAPER_8.5X11_BOTTOM_HALF_LABEL': 'PAPER_85X11_BOTTOM_HALF_LABEL',
    'PAPER_8.5X11_TOP_HALF_LABEL': 'PAPER_85X11_TOP_HALF_LABEL',
    'STOCK_4X6.75': 'STOCK_4X675',
    'STOCK_4X6.75_LEADING_DOC_TAB': 'STOCK_4X675_LEADING_DOC_TAB',
    'STOCK_4X6.75_TRAILING_DOC_TAB': 'STOCK_4X675_TRAILING_DOC_TAB',
}

class FedexRequest:
    def __init__(self, carrier):
        super_carrier = carrier.sudo()
        self.base_url = PROD_BASE_URL if super_carrier.prod_environment else TEST_BASE_URL
        self.access_token = super_carrier.fedex_rest_access_token
        self.client_id = super_carrier.fedex_rest_developer_key
        self.client_secret = super_carrier.fedex_rest_developer_password
        self.account_number = super_carrier.fedex_rest_account_number
        self.weight_units = super_carrier.fedex_rest_weight_unit
        self.vat_override = super_carrier.fedex_rest_override_shipper_vat
        self.email_notifications = super_carrier.fedex_rest_email_notifications
        self.documentation_type = super_carrier.fedex_rest_documentation_type
        self.insurance = super_carrier.shipping_insurance
        self.check_residential = super_carrier.fedex_rest_residential_address
        self.dropoff_type = super_carrier.fedex_rest_droppoff_type
        self.service_type = super_carrier.fedex_rest_service_type
        self.label_stock = _convert_stock_type(super_carrier.fedex_rest_label_stock_type)
        self.label_file = super_carrier.fedex_rest_label_file_type
        self.duty_payment = super_carrier.fedex_rest_duty_payment
        self.make_return = super_carrier.return_label_on_delivery
        self.debug_logger = super_carrier.log_xml
        self.carrier = super_carrier
        self.session = requests.Session()

    def _send_fedex_request(self, url, data, method='POST'):
        new_token = False
        if not self.access_token:
            self.access_token = self._get_new_access_token()
            self.carrier.fedex_rest_access_token = self.access_token
            new_token = True

        def _request_call():
            try:
                response = self.session.request(method, self.base_url + url, json=data, headers={
                        'Content-Type': "application/json",
                        'Authorization': "Bearer " + self.access_token
                    }, timeout=15
                )
                self.debug_logger("%s %s\n%s\n\n%s" % (
                    response.request.method,
                    response.request.url,
                    '\n'.join([f'{k}: {v}' for k, v in response.request.headers.items()]),
                    response.request.body.decode('utf-8')
                ), 'fedex_rest_request')
                self.debug_logger("%s %s\n%s\n\n%s" % (
                    response.status_code,
                    response.reason,
                    '\n'.join([f'{k}: {v}' for k, v in response.headers.items()]),
                    response.text
                ), 'fedex_rest_response')
            except RequestException:
                raise ValidationError(_('Something went wrong, please try again later!!')) from None
            return response

        res = _request_call()
        if res.status_code == 401 and not new_token:
            self.access_token = self._get_new_access_token()
            self.carrier.fedex_rest_access_token = self.access_token
            res = _request_call()

        try:
            response_data = res.json()
        except JSONDecodeError:
            raise ValidationError(_('Could not decode response')) from None
        if not res.ok:
            raise ValidationError(self._process_errors(response_data))
        if 'output' not in response_data:
            raise ValidationError(_('Could not decode response'))

        return response_data['output']

    def _process_errors(self, res_body):
        err_msgs = []
        for err in res_body.get('errors', []):
            err_msgs.append(f"{err['message']} ({err['code']})")
        return ','.join(err_msgs)

    def _process_alerts(self, response):
        messages = []
        alerts = response.get('alerts', [])
        if 'rateReplyDetails' in response:
            alerts += response['rateReplyDetails'][0].get('customerMessages', [])
        for alert in alerts:
            messages.append(f"{alert['message']} ({alert['code']})")

        return '\n'.join(messages)

    def _get_new_access_token(self):
        if not self.client_id or not self.client_secret:
            raise ValidationError(_('You must setup a client ID and secret on the carrier first'))
        try:
            response = self.session.post(
                self.base_url + "/oauth/token",
                f"grant_type=client_credentials&client_id={self.client_id}&client_secret={self.client_secret}",
                headers={'Content-Type': "application/x-www-form-urlencoded"},
                timeout=15
            )
            response_data = response.json()
        except RequestException:
            raise ValidationError(_('Something went wrong, please try again later!!')) from None
        except JSONDecodeError:
            raise ValidationError(_('Could not decode response')) from None
        if not response.ok:
            raise ValidationError(self._process_errors(response_data))
        if 'access_token' not in response_data:
            raise ValidationError(_('Could not decode response'))

        return response_data['access_token']

    def _parse_state_code(self, state_code, country_code):
        if country_code == 'CH':
            # For Switzerland, keep the part before the hyphen
            return state_code.split('-')[0]
        else:
            # For other countries, keep the part after the hyphen
            split_code = state_code.split('-')
            if split_code[0] == country_code and len(split_code) > 1:
                return split_code[1]
            else:
                return state_code

    def _get_location_from_partner(self, partner, check_residential=False):
        res = {'countryCode': partner.country_id.code}
        if partner.city:
            res['city'] = remove_accents(partner.city)
        if partner.zip:
            res['postalCode'] = partner.zip
        if partner.state_id:
            state_code = self._parse_state_code(partner.state_id.code, partner.country_id.code)
        # need to adhere to two character length state code
            if partner.country_id.code == 'MX':
                state_code = FEDEX_MX_STATE_MATCH[state_code]
            if partner.country_id.code == 'AE':
                state_code = FEDEX_AE_STATE_MATCH.get(state_code, state_code)
            if partner.country_id.code == 'IN' and partner.state_id.code == 'UK':
                state_code = 'UT'
            if len(state_code) <= 2:
                res['stateOrProvinceCode'] = state_code
        if check_residential:
            setting = self.check_residential
            if setting == 'always' or (setting == 'check' and self._check_residential_address({**res, 'streetLines': [partner.street, partner.street2]})):
                res['residential'] = True
        return res

    def _check_residential_address(self, address):
        if not address['streetLines'][1]:
            del address['streetLines'][1]
        result = self._send_fedex_request('/address/v1/addresses/resolve', {
            'addressesToValidate': [{'address': address}]
        })
        return result['resolvedAddresses'][0]['classification'] != 'BUSINESS'  # We assume residential until proven otherwise

    def _get_address_from_partner(self, partner, check_residential=False):
        res = self._get_location_from_partner(partner, check_residential)
        res['streetLines'] = [remove_accents(partner.street)]
        if partner.street2:
            res['streetLines'].append(remove_accents(partner.street2))
        return res

    def _get_contact_from_partner(self, partner, company_partner=False):
        res = {'phoneNumber': partner.phone or partner.mobile}
        if company_partner and not res['phoneNumber']:
            # Fallback to phone on the company if none on the WH
            res['phoneNumber'] = company_partner.phone or company_partner.mobile
        if company_partner:
            # Always put the name of the company, if the partner is a WH
            res['companyName'] = partner.name[:35]
            res['personName'] = partner.name[:70]
        elif partner.is_company:
            res['companyName'] = partner.name[:35]
            res['personName'] = partner.name[:70]
        else:
            res['personName'] = partner.name[:70]
            if partner.parent_id:
                res['companyName'] = partner.parent_id.name[:35]
            elif partner.company_name:
                res['companyName'] = partner.company_name[:35]
        if partner.email:
            res['emailAddress'] = partner.email
        elif company_partner and company_partner.email:
            res['emailAddress'] = company_partner.email
        return res

    def _get_package_info(self, package):
        res = {
            'weight': {
                'units': self.weight_units,
                'value': self.carrier._fedex_rest_convert_weight(package.weight)
            },
        }
        if int(package.dimension['length']) or int(package.dimension['width']) or int(package.dimension['height']):
            # FedEx will raise a warning when mixing imperial and metric units (MIXED.MEASURING.UNITS.INCLUDED).
            # So we force the dimension unit based on the selected weight unit on the delivery method.
            res['dimensions'] = {
                'units': 'IN' if self.weight_units == 'LB' else 'CM',
                'length': int(package.dimension['length']),
                'width': int(package.dimension['width']),
                'height': int(package.dimension['height']),
            }
        if self.insurance:
            res['declaredValue'] = {
                'amount': float_repr(package.total_cost * self.insurance / 100, 2),
                'currency': _convert_curr_iso_fdx(package.currency_id.name),
            }
        return res

    def _get_detailed_package_info(self, package, customPackaging, order_no=False):
        res = self._get_package_info(package)
        if customPackaging:
            res['subPackagingType'] = 'PACKAGE'
        description = ', '.join([c.product_id.name for c in package.commodities])
        res['itemDescription'] = description[:50]
        res['itemDescriptionForClearance'] = description
        if order_no:
            res['customerReferences'] = [{
                'customerReferenceType': 'P_O_NUMBER',
                'value': order_no
            }]
        return res

    def _get_commodities_info(self, commodity, currency):
        res = {
            'description': commodity.product_id.name[:450],
            'customsValue': ({'amount': commodity.monetary_value * commodity.qty, 'currency': currency}),
            'unitPrice': ({'amount': commodity.monetary_value, 'currency': currency}),
            'countryOfManufacture': commodity.country_of_origin,
            'weight': {
                'units': self.weight_units,
                'value': self.carrier._fedex_rest_convert_weight(commodity.product_id.weight),
            },
            'quantity': commodity.qty,
            'quantityUnits': commodity.product_id.uom_id.fedex_code,
            'numberOfPieces': 1,
        }
        if commodity.product_id.hs_code:
            res['harmonizedCode'] = commodity.product_id.hs_code
        return res

    def _get_tins_from_partner(self, partner, custom_vat=False):
        def _transform_vat_to_fedex_format(vat_number):
            if not vat_number:
                return ''
            if len(vat_number) > 18:
                return re.sub(r'[^A-Za-z0-9 ]', '', vat_number)
            return vat_number

        res = []
        if custom_vat:
            res.append({
                'number': _transform_vat_to_fedex_format(self.vat_override),
                'tinType': 'BUSINESS_UNION'
            })
        if partner.vat and partner.is_company:
            res.append({'number': _transform_vat_to_fedex_format(partner.vat), 'tinType': 'BUSINESS_NATIONAL'})
        elif partner.parent_id and partner.parent_id.vat and partner.parent_id.is_company:
            res.append({'number': _transform_vat_to_fedex_format(partner.parent_id.vat), 'tinType': 'BUSINESS_NATIONAL'})
        return res

    def _get_shipping_price(self, ship_from, ship_to, packages, currency):
        fedex_currency = _convert_curr_iso_fdx(currency)
        request_data = {
            'accountNumber': {'value': self.account_number},
            'requestedShipment': {
                'rateRequestType': ['PREFERRED'],
                'preferredCurrency': fedex_currency,
                'pickupType': self.dropoff_type,
                'serviceType': self.service_type,
                'packagingType': packages[0].packaging_type,
                'shipper': {'address': self._get_location_from_partner(ship_from)},
                'recipient': {'address': self._get_location_from_partner(ship_to, True)},
                'requestedPackageLineItems': [self._get_package_info(p) for p in packages],
                'customsClearanceDetail': {
                    'commercialInvoice': {'shipmentPurpose': 'SOLD'},
                    'commodities': [self._get_commodities_info(c, fedex_currency) for pkg in packages for c in pkg.commodities],
                    'freightOnValue': 'CARRIER_RISK' if self.insurance == 100 else 'OWN_RISK',
                    'dutiesPayment': {'paymentType': 'SENDER'}  # Only allowed value...
                }
            }
        }
        self._add_extra_data_to_request(request_data, 'rate')
        res = self._send_fedex_request("/rate/v1/rates/quotes", request_data)
        try:
            rate = next(filter(lambda d: d['currency'] == fedex_currency, res['rateReplyDetails'][0]['ratedShipmentDetails']), {})
            if rate.get('totalNetChargeWithDutiesAndTaxes', 0):
                price = rate['totalNetChargeWithDutiesAndTaxes']
            else:
                price = rate['totalNetCharge']
        except KeyError:
            raise ValidationError(_('Could not decode response')) from None

        return {
            'price': price,
            'alert_message': self._process_alerts(res),
        }

    def _ship_package(self, ship_from_wh, ship_from_company, ship_to, sold_to, packages, currency, order_no, customer_ref, picking_no, incoterms, freight_charge):
        fedex_currency = _convert_curr_iso_fdx(currency)
        package_type = packages[0].packaging_type
        request_data = {
            'accountNumber': {'value': self.account_number},
            'labelResponseOptions': 'LABEL',
            'requestedShipment': {
                'rateRequestType': ['PREFERRED'],
                'preferredCurrency': fedex_currency,
                'pickupType': self.dropoff_type,
                'serviceType': self.service_type,
                'packagingType': package_type,
                'shippingChargesPayment': {'paymentType': 'SENDER'},
                'labelSpecification': {'labelStockType': self.label_stock, 'imageType': self.label_file},
                'shipper': {
                    'address': self._get_address_from_partner(ship_from_wh),
                    'contact': self._get_contact_from_partner(ship_from_wh, ship_from_company),
                    'tins': self._get_tins_from_partner(ship_from_company, self.vat_override),
                },
                'recipients': [{
                    'address': self._get_address_from_partner(ship_to, True),
                    'contact': self._get_contact_from_partner(ship_to),
                    'tins': self._get_tins_from_partner(ship_to),
                }],
                'requestedPackageLineItems': [self._get_detailed_package_info(p, package_type == 'YOUR_PACKAGING', order_no) for p in packages],
                'customsClearanceDetail': {
                    'dutiesPayment': {'paymentType': self.duty_payment},
                    'commodities': [self._get_commodities_info(c, fedex_currency) for pkg in packages for c in pkg.commodities],
                    'commercialInvoice': {
                        'shipmentPurpose': 'SOLD',
                        'originatorName': ship_from_company.name,
                        'comments': ['', picking_no],  # First one is special instructions
                    },
                }
            }
        }
        if freight_charge:
            request_data['requestedShipment']['customsClearanceDetail']['commercialInvoice']['freightCharge'] = {
                'amount': freight_charge,
                'currency': fedex_currency,
            }
        if incoterms:
            request_data['requestedShipment']['customsClearanceDetail']['commercialInvoice']['termsOfSale'] = incoterms
        if customer_ref:
            request_data['requestedShipment']['customsClearanceDetail']['commercialInvoice']['customerReferences'] = [{
                'customerReferenceType': 'CUSTOMER_REFERENCE',
                'value': customer_ref,
            }]
        if request_data['requestedShipment']['shipper']['address']['countryCode'] == 'IN' and request_data['requestedShipment']['recipients'][0]['address']['countryCode'] == 'IN':
            request_data['requestedShipment']['customsClearanceDetail']['freightOnValue'] = 'CARRIER_RISK' if self.insurance == 100 else 'OWN_RISK'
        if sold_to and sold_to != ship_to:
            request_data['requestedShipment']['soldTo'] = {
                'address': self._get_address_from_partner(sold_to),
                'contact': self._get_contact_from_partner(sold_to),
                'tins': self._get_tins_from_partner(sold_to),
            }
        if ship_to.vat or ship_to.parent_id.vat:
            request_data['requestedShipment']['customsClearanceDetail']['recipientCustomsId'] = {
                'type': 'COMPANY',
                'value': ship_to.vat or ship_to.parent_id.vat,
            }
        if self.email_notifications and ship_to.email:
            request_data['requestedShipment']['emailNotificationDetail'] = {
                'aggregationType': 'PER_PACKAGE',
                'emailNotificationRecipients': [{
                    'emailNotificationRecipientType': 'RECIPIENT',
                    'emailAddress': ship_to.email,
                    'name': ship_to.name,
                    'notificationFormatType': 'HTML',
                    'notificationType': 'EMAIL',
                    'notificationEventType': ['ON_DELIVERY', 'ON_EXCEPTION', 'ON_SHIPMENT', 'ON_TENDER', 'ON_ESTIMATED_DELIVERY']
                }]
            }
        if self.documentation_type != 'none':
            request_data['requestedShipment']['shippingDocumentSpecification'] = {
                'shippingDocumentTypes': ['COMMERCIAL_INVOICE'],
                'commercialInvoiceDetail': {
                    'documentFormat': {'stockType': 'PAPER_LETTER', 'docType': 'PDF'}
                }
            }
        if self.documentation_type == 'etd':
            request_data['requestedShipment']['shipmentSpecialServices'] = {
                "specialServiceTypes": [
                    "ELECTRONIC_TRADE_DOCUMENTS"
                ],
                "etdDetail": {
                    "requestedDocumentTypes": [
                        "COMMERCIAL_INVOICE"
                    ]
                }
            }
        if self.make_return:
            request_data['requestedShipment']['customsClearanceDetail']['customsOption'] = {'type': 'COURTESY_RETURN_LABEL'}

        self._add_extra_data_to_request(request_data, 'ship')
        res = self._send_fedex_request("/ship/v1/shipments", request_data)

        try:
            shipment = res['transactionShipments'][0]
            details = shipment['completedShipmentDetail']
            pieces = shipment['pieceResponses']
            # Sometimes the shipment might be created but no pricing calculated, we just set to 0.
            price = self._decode_pricing(details['shipmentRating'], fedex_currency) if 'shipmentRating' in details else 0.0
        except KeyError:
            raise ValidationError(_('Could not decode response')) from None

        return {
            'service_info': f"{details.get('carrierCode', '')} > {details.get('serviceDescription', {}).get('description', '')} > {details.get('packagingDescription', '')}",
            'tracking_numbers': ','.join([
                t.get('trackingNumber', '')
                for pkg in details.get('completedPackageDetails', [])
                for t in pkg.get('trackingIds', [])
            ]),
            'labels': [
                (
                    p.get('trackingNumber', ''),
                    next(filter(lambda d: d.get('contentType', '') == 'LABEL', p.get('packageDocuments', {})), {}).get('encodedLabel')
                )
                for p in pieces
            ],
            'price': price,
            'documents': ', '.join([
                f"{d.get('minimumCopiesRequired')}x {d.get('type', '')}"
                for d in details.get('documentRequirements', {}).get('generationDetails', {})
                if d.get('minimumCopiesRequired', 0)
            ]),
            'alert_message': self._process_alerts(shipment),
            'invoice': next(filter(
                lambda d: d.get('contentType', '') == 'COMMERCIAL_INVOICE',
                shipment.get('shipmentDocuments', {})
            ), {}).get('encodedLabel', ''),
            'date': shipment.get('shipDatestamp', ''),
        }

    def _return_package(self, ship_from, ship_to_company, ship_to_wh, packages, currency, tracking, date):
        fedex_currency = _convert_curr_iso_fdx(currency)
        package_type = packages[0].packaging_type
        request_data = {
            'accountNumber': {'value': self.account_number},
            'labelResponseOptions': 'LABEL',
            'requestedShipment': {
                'rateRequestType': ['PREFERRED'],
                'preferredCurrency': fedex_currency,
                'pickupType': self.dropoff_type,
                'serviceType': self.service_type,
                'packagingType': package_type,
                'shippingChargesPayment': {'paymentType': 'SENDER'},
                'shipmentSpecialServices': {
                    'specialServiceTypes': ['RETURN_SHIPMENT'],
                    'returnShipmentDetail': {
                        'returnType': 'PRINT_RETURN_LABEL',
                        'returnAssociationDetail': {'trackingNumber': tracking, 'shipDatestamp': date},
                    }
                },
                'labelSpecification': {'labelStockType': self.label_stock, 'imageType': self.label_file},
                'shipper': {
                    'address': self._get_address_from_partner(ship_from),
                    'contact': self._get_contact_from_partner(ship_from),
                    'tins': self._get_tins_from_partner(ship_from),
                },
                'recipients': [{
                    'address': self._get_address_from_partner(ship_to_wh, True),
                    'contact': self._get_contact_from_partner(ship_to_wh, ship_to_company),
                    'tins': self._get_tins_from_partner(ship_to_company, self.vat_override),
                }],
                'requestedPackageLineItems': [self._get_detailed_package_info(p, package_type == 'YOUR_PACKAGING') for p in packages],
                'customsClearanceDetail': {
                    'dutiesPayment': {'paymentType': 'SENDER'},  # Only allowed value for returns
                    'commodities': [self._get_commodities_info(c, fedex_currency) for pkg in packages for c in pkg.commodities],
                    'customsOption': {'type': 'REJECTED'},
                }
            }
        }
        if request_data['requestedShipment']['shipper']['address']['countryCode'] == 'IN' and request_data['requestedShipment']['recipients'][0]['address']['countryCode'] == 'IN':
            request_data['requestedShipment']['customsClearanceDetail']['freightOnValue'] = 'CARRIER_RISK' if self.insurance == 100 else 'OWN_RISK'
        if self.vat_override or ship_to_company.vat:
            request_data['requestedShipment']['customsClearanceDetail']['recipientCustomsId'] = {
                'type': 'COMPANY',
                'value': self.vat_override or ship_to_company.vat,
            }

        self._add_extra_data_to_request(request_data, 'return')
        res = self._send_fedex_request("/ship/v1/shipments", request_data)

        try:
            shipment = res['transactionShipments'][0]
            details = shipment['completedShipmentDetail']
            pieces = shipment['pieceResponses']
        except KeyError:
            raise ValidationError(_('Could not decode response')) from None

        return {
            'tracking_numbers': ','.join([
                t.get('trackingNumber', '')
                for pkg in details.get('completedPackageDetails', [])
                for t in pkg.get('trackingIds', [])
            ]),
            'labels': [
                (
                    p.get('trackingNumber', ''),
                    next(filter(lambda d: d.get('contentType', '') == 'LABEL', p.get('packageDocuments', {})), {}).get('encodedLabel')
                )
                for p in pieces
            ],
            'documents': ', '.join([
                f"{d.get('minimumCopiesRequired')}x {d.get('type', '')}"
                for d in details.get('documentRequirements', {}).get('generationDetails', {})
                if d.get('minimumCopiesRequired', 0)
            ]),
            'alert_message': self._process_alerts(shipment),
        }

    def _decode_pricing(self, rating_result, request_currency=False):
        actual = next(filter(
            lambda d:
                d['rateType'] in [rating_result['actualRateType'], rating_result['actualRateType'].replace("PAYOR", "PREFERRED").replace("RATED", "PREFERRED")] and
                (not request_currency or d['currency'] == request_currency),
            rating_result['shipmentRateDetails']
        ), {})
        if actual.get('totalNetChargeWithDutiesAndTaxes', False):
            return actual['totalNetChargeWithDutiesAndTaxes']
        return actual['totalNetCharge']

    def cancel_shipment(self, tracking_nr):
        res = self._send_fedex_request('/ship/v1/shipments/cancel', {
            'accountNumber': {'value': self.account_number},
            'deletionControl': 'DELETE_ALL_PACKAGES',  # Cancel the entire shipment, not only the individual package.
            'trackingNumber': tracking_nr,
        }, 'PUT')
        if not res.get('cancelledShipment', False):
            return {
                'delete_success': False,
                'errors_message': res.get('message', 'Cancel shipment failed. Reason unknown.'),
            }
        return {
            'delete_success': True,
            'alert_message': self._process_alerts(res),
        }

    def _add_extra_data_to_request(self, request, request_type):
        """Adds the extra data to the request.
        When there are multiple items in a list, they will all be affected by
        the change.
        """
        extra_data_input = {
            'rate': self.carrier.fedex_rest_extra_data_rate_request,
            'ship': self.carrier.fedex_rest_extra_data_ship_request,
            'return': self.carrier.fedex_rest_extra_data_return_request,
        }.get(request_type) or ''
        try:
            extra_data = json.loads('{' + extra_data_input + '}')
        except SyntaxError:
            raise UserError(_('Invalid syntax for FedEx extra data.')) from None

        def extra_data_to_request(request, extra_data):
            """recursive function that adds extra data to the current request."""
            for key, new_value in extra_data.items():
                request[key] = current_value = request.get(key)
                if isinstance(current_value, list):
                    for item in current_value:
                        extra_data_to_request(item, new_value)
                elif isinstance(new_value, dict) and isinstance(current_value, dict):
                    extra_data_to_request(current_value, new_value)
                else:
                    request[key] = new_value

        extra_data_to_request(request, extra_data)


def _convert_curr_fdx_iso(code):
    curr_match = {v: k for k, v in FEDEX_CURR_MATCH.items()}
    return curr_match.get(code, code)


def _convert_curr_iso_fdx(code):
    return FEDEX_CURR_MATCH.get(code, code)


def _convert_stock_type(stock_type):
    return FEDEX_STOCK_TYPE_MATCH.get(stock_type, stock_type)
