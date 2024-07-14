import requests
import re
import base64
import io
# activate PDF support in PIL
import PIL.PdfImagePlugin  # pylint: disable=W0611
from PIL import Image
from json.decoder import JSONDecodeError
from requests.exceptions import RequestException
from werkzeug.urls import url_join

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools import float_repr

TEST_BASE_URL = "https://wwwcie.ups.com"
PROD_BASE_URL = "https://onlinetools.ups.com"
API_VERSION = "v1"
TOKEN_TYPE = "Bearer"


class UPSRequest:

    def __init__(self, carrier):
        super_carrier = carrier.sudo()
        self.logger = carrier.log_xml
        self.base_url = PROD_BASE_URL if carrier.prod_environment else TEST_BASE_URL
        self.access_token = super_carrier.ups_access_token
        self.client_id = super_carrier.ups_client_id
        self.client_secret = super_carrier.ups_client_secret
        self.shipper_number = super_carrier.ups_shipper_number
        self.carrier = carrier
        self.session = requests.Session()

    def _send_request(self, url, method='GET', data=None, json=None, headers=None, auth=None):
        url = url_join(self.base_url, url)

        def _request_call(req_headers):
            if not req_headers and self.access_token:
                req_headers = {
                    "Authorization": '%s %s' % (TOKEN_TYPE, self.access_token)
                }
            self.logger(f'{url}\n{method}\n{req_headers}\n{data}\n{json}', f'ups request {url}')
            try:
                res = self.session.request(method=method, url=url, json=json, data=data, headers=req_headers, auth=auth, timeout=15)
                self.logger(f'{res.status_code} {res.text}', f'ups response {url}')
            except RequestException as err:
                self.logger(str(err), f'ups response {url}')
                raise ValidationError(_('Something went wrong, please try again later!!'))
            return res

        res = _request_call(headers)
        if res.status_code == 401 and auth is None:
            self.access_token = self._get_new_access_token()
            self.carrier.sudo().ups_access_token = self.access_token
            res = _request_call(None)

        return res

    def _process_errors(self, res_body):
        err_msgs = []
        response = res_body.get('response')
        if response:
            for err in response.get('errors', []):
                err_msgs.append(err['message'])
        return ','.join(err_msgs)

    def _process_alerts(self, response):
        alerts = response.get('Alert', [])
        if isinstance(alerts, list):
            messages = [alert['Description'] for alert in alerts]
            return '\n'.join(messages)
        return alerts['Description']

    def _get_new_access_token(self):
        if not self.client_id or not self.client_secret:
            raise ValidationError(_('You must setup a client ID and secret on the carrier first'))
        url = '/security/v1/oauth/token'
        headers = {
            'x-merchant-id': self.client_id
        }
        data = {
            "grant_type": "client_credentials"
        }
        res = self._send_request(url, 'POST', data=data, headers=headers, auth=(self.client_id, self.client_secret))
        try:
            res_body = res.json()
        except JSONDecodeError as err:
            self.logger(str(err), f'ups response decode error {url}')
            raise ValidationError(_('Could not decode response'))
        if not res.ok:
            raise ValidationError(self._process_errors(res_body))
        return res_body.get('access_token')

    def _clean_phone_number(self, phone):
        return re.sub('[^0-9]', '', phone)

    def _save_label(self, image64, label_file_type='GIF'):
        img_decoded = base64.decodebytes(image64.encode('utf-8'))
        if label_file_type == 'GIF':
            # Label format is GIF, so need to rotate and convert as PDF
            image_string = io.BytesIO(img_decoded)
            im = Image.open(image_string)
            label_result = io.BytesIO()
            im.save(label_result, 'pdf')
            return label_result.getvalue()
        else:
            return img_decoded

    def _check_required_value(self, order=False, picking=False, is_return=False):
        if order:
            shipper = order.company_id.partner_id
            ship_from = order.warehouse_id.partner_id
            ship_to = order.partner_shipping_id
        elif picking and is_return:
            ship_from = shipper = picking.partner_id
            ship_to = picking.picking_type_id.warehouse_id.partner_id
        else:
            shipper = picking.company_id.partner_id
            ship_from = picking.picking_type_id.warehouse_id.partner_id
            ship_to = picking.partner_id
        required_field = {'city': 'City', 'country_id': 'Country', 'phone': 'Phone'}
        # Check required field for shipper
        res = [required_field[field] for field in required_field if not shipper[field]]
        if shipper.country_id.code in ('US', 'CA', 'IE') and not shipper.state_id.code:
            res.append('State')
        if not shipper.street and not shipper.street2:
            res.append('Street')
        if shipper.country_id.code != 'HK' and not shipper.zip:
            res.append('ZIP code')
        if res:
            return _("The address of your company is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        if len(self._clean_phone_number(shipper.phone)) < 10:
            return _("Shipper Phone must be at least 10 alphanumeric characters.")
        # Check required field for warehouse address
        res = [required_field[field] for field in required_field if not ship_from[field]]
        if ship_from.country_id.code in ('US', 'CA', 'IE') and not ship_from.state_id.code:
            res.append('State')
        if not ship_from.street and not ship_from.street2:
            res.append('Street')
        if ship_from.country_id.code != 'HK' and not ship_from.zip:
            res.append('ZIP code')
        if res:
            return _("The address of your warehouse is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        if len(self._clean_phone_number(ship_from.phone)) < 10:
            return _("Warehouse Phone must be at least 10 alphanumeric characters."),
        # Check required field for recipient address
        res = [required_field[field] for field in required_field if field != 'phone' and not ship_to[field]]
        if ship_to.country_id.code in ('US', 'CA', 'IE') and not ship_to.state_id.code:
            res.append('State')
        if not ship_to.street and not ship_to.street2:
            res.append('Street')
        if ship_to.country_id.code != 'HK' and not ship_to.zip:
            res.append('ZIP code')
        if len(ship_to.street or '') > 35 or len(ship_to.street2 or '') > 35:
            return _("UPS address lines can only contain a maximum of 35 characters. You can split the contacts addresses on multiple lines to try to avoid this limitation.")
        if picking and not order:
            order = picking.sale_id
        phone = ship_to.mobile or ship_to.phone
        if order and not phone:
            phone = order.partner_id.mobile or order.partner_id.phone
        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            for line in order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type not in ['service', 'digital', False]):
                return _('The estimated price cannot be computed because the weight of your product %s is missing.', line.product_id.display_name)
        if picking:
            for ml in picking.move_line_ids.filtered(lambda ml: not ml.result_package_id and not ml.product_id.weight):
                return _("The delivery cannot be done because the weight of your product %s is missing.", ml.product_id.display_name)
            packages_without_weight = picking.move_line_ids.mapped('result_package_id').filtered(lambda p: not p.shipping_weight)
            if packages_without_weight:
                return _('Packages %s do not have a positive shipping weight.', ', '.join(packages_without_weight.mapped('display_name')))
        if not phone:
            res.append('Phone')
        if res:
            return _("The recipient address is missing or wrong.\n(Missing field(s) : %s)", ",".join(res))
        if len(self._clean_phone_number(phone)) < 10:
            return _("Recipient Phone must be at least 10 alphanumeric characters."),
        return False

    def _set_package_details(self, packages, carrier, ship_from, ship_to, cod_info, ship=False, is_return=False):
        # Package Type key in ship request and rate request are different
        package_type_key = 'Packaging' if ship else 'PackagingType'
        res_packages = []
        for p in packages:
            package = {
                package_type_key: {
                    'Code': p.packaging_type or '00',
                },
                'Description': 'Return of package' if is_return else None,
                'PackageWeight': {
                    'UnitOfMeasurement': {
                        'Code': carrier.ups_package_weight_unit,
                    },
                    'Weight': str(carrier._ups_convert_weight(p.weight, carrier.ups_package_weight_unit)),
                },
                'Dimensions': {
                    'UnitOfMeasurement': {
                        'Code': carrier.ups_package_dimension_unit or '',
                    },
                    'Length': str(p.dimension['length']) or '',
                    'Width': str(p.dimension['width']) or '',
                    'Height': str(p.dimension['height']) or '',
                }
            }

            package_service_options = {}

            if cod_info:
                package_service_options['COD'] = {
                    'CODFundsCode': cod_info['funds_code'],
                    'CODAmount': {
                        'MonetaryValue': str(cod_info['monetary_value']),
                        'CurrencyCode': cod_info['currency'],
                    }
                }
            if p.currency_id:
                package_service_options['DeclaredValue'] = {
                    'CurrencyCode': p.currency_id.name,
                    'MonetaryValue': float_repr(p.total_cost * carrier.shipping_insurance / 100, 2),
                }

            if package_service_options:
                package['PackageServiceOptions'] = package_service_options

            # Package and shipment reference text is only allowed for shipments within
            # the USA and within Puerto Rico. This is a UPS limitation.
            if (p.name and ' ' not in p.name and ship_from.country_id.code in ('US') and ship_to.country_id.code in ('US')):
                package.update({
                    'ReferenceNumber': {
                        'Code': 'PM',
                        'Value': p.name,
                        'BarCodeIndicator': p.name,
                    }
                })
            res_packages.append(package)
        return res_packages

    def _get_ship_data_from_partner(self, partner, shipper_no=None):
        return {
            'AttentionName': (partner.name or '')[:35],
            'Name': (partner.parent_id.name or partner.name or '')[:35],
            'EMailAddress': partner.email or '',
            'ShipperNumber': shipper_no or '',
            'Phone': {
                'Number': (partner.phone or partner.mobile or '').replace(' ', ''),
            },
            'Address': {
                'AddressLine': [partner.street or '', partner.street2 or ''],
                'City': partner.city or '',
                'PostalCode': partner.zip or '',
                'CountryCode': partner.country_id.code or '',
                'StateProvinceCode': partner.state_id.code or '',
            },
        }

    def _get_shipping_price(self, shipper, ship_from, ship_to, total_qty, packages, carrier, cod_info=None):
        service_type = carrier.ups_default_service_type
        saturday_delivery = carrier.ups_saturday_delivery
        url = f'/api/rating/{API_VERSION}/Rate'
        data = {
            'RateRequest': {
                'Request': {
                    'RequestOption': 'Rate',
                },
                'Shipment': {
                    'Package': self._set_package_details(packages, carrier, ship_from, ship_to, cod_info),
                    'Shipper': self._get_ship_data_from_partner(shipper, self.shipper_number),
                    'ShipFrom': self._get_ship_data_from_partner(ship_from),
                    'ShipTo': self._get_ship_data_from_partner(ship_to),
                    'Service': {
                        'Code': service_type,
                    },
                    'NumOfPieces': str(int(total_qty)) if service_type == '96' else None,
                    'ShipmentServiceOptions': {'SaturdayDeliveryIndicator': saturday_delivery} if saturday_delivery else None,
                    'ShipmentRatingOptions': {
                        'NegotiatedRatesIndicator': "1",
                    }
                }
            },
        }
        res = self._send_request(url, method='POST', json=data)
        if not res.ok:
            return {'error_message': self._process_errors(res.json())}

        res = res.json()
        rate = res['RateResponse']['RatedShipment']
        charge = rate['TotalCharges']

        # Some users are qualified to receive negotiated rates
        if 'NegotiatedRateCharges' in rate and rate['NegotiatedRateCharges']['TotalCharge']['MonetaryValue']:
            charge = rate['NegotiatedRateCharges']['TotalCharge']

        return {
            'currency_code': charge['CurrencyCode'],
            'price': charge['MonetaryValue'],
            'alert_message': self._process_alerts(res['RateResponse']['Response']),
        }

    def _set_invoice(self, shipment_info, commodities, ship_to, is_return):
        invoice_products = []
        for commodity in commodities:
            # split the name of the product to maximum 3 substrings of length 35
            name = commodity.product_id.name
            product = {
                'Description': [line for line in [name[35 * i:35 * (i + 1)] for i in range(3)] if line],
                'Unit': {
                    'Number': str(int(commodity.qty)),
                    'UnitOfMeasurement': {
                        'Code': 'PC' if commodity.qty == 1 else 'PCS',
                    },
                    'Value': float_repr(commodity.monetary_value, 2)
                },
                'OriginCountryCode': commodity.country_of_origin,
                'CommodityCode': commodity.product_id.hs_code or '',
            }
            invoice_products.append(product)
        if len(ship_to.commercial_partner_id.name) > 35:
            raise ValidationError(_('The name of the customer should be no more than 35 characters.'))
        contacts = {
            'SoldTo': {
                'Name': ship_to.commercial_partner_id.name,
                'AttentionName': ship_to.name,
                'Address': {
                    'AddressLine': [line for line in (ship_to.street, ship_to.street2) if line],
                    'City': ship_to.city,
                    'PostalCode': ship_to.zip,
                    'CountryCode': ship_to.country_id.code,
                    'StateProvinceCode': ship_to.state_id.code or '' if ship_to.country_id.code in ('US', 'CA', 'IE') else None
                }
            }
        }
        return {
            'FormType': '01',
            'Product': invoice_products,
            'CurrencyCode': shipment_info.get('itl_currency_code'),
            'InvoiceDate': shipment_info.get('invoice_date'),
            'ReasonForExport': 'RETURN' if is_return else 'SALE',
            'Contacts': contacts,
        }

    def _send_shipping(self, shipment_info, packages, carrier, shipper, ship_from, ship_to, service_type, duty_payment,
                       saturday_delivery=False, cod_info=None, label_file_type='GIF', ups_carrier_account=False, is_return=False):
        url = f'/api/shipments/{API_VERSION}/ship'
        # Payment Info
        shipment_charge = {
            'Type': '01',
        }
        payment_info = [shipment_charge]
        if ups_carrier_account:
            shipment_charge['BillReceiver'] = {
                'AccountNumber': ups_carrier_account,
                'Address': {
                    'PostalCode': ship_to.zip,
                }
            }
        else:
            shipment_charge['BillShipper'] = {
                'AccountNumber': self.shipper_number,
            }
        if duty_payment == 'SENDER':
            payment_info.append({
                'Type': '02',
                'BillShipper': {'AccountNumber': self.shipper_number},
            })
        shipment_service_options = {}
        if shipment_info.get('require_invoice'):
            shipment_service_options['InternationalForms'] = self._set_invoice(shipment_info, [c for pkg in packages for c in pkg.commodities],
                                                                               ship_to, is_return)
            shipment_service_options['InternationalForms']['PurchaseOrderNumber'] = shipment_info.get('purchase_order_number')
            shipment_service_options['InternationalForms']['TermsOfShipment'] = shipment_info.get('terms_of_shipment')
        if saturday_delivery:
            shipment_service_options['SaturdayDeliveryIndicator'] = saturday_delivery

        request = {
            'ShipmentRequest': {
                'Request': {
                    'RequestOption': 'nonvalidate',
                },
                'LabelSpecification': {
                    'LabelImageFormat': {
                        'Code': label_file_type,
                    },
                    'LabelStockSize': {'Height': '6', 'Width': '4'} if label_file_type != 'GIF' else None,
                },
                'Shipment': {
                    'Description': shipment_info.get('description'),
                    'ReturnService': {'Code': '9'}if is_return else None,
                    'Package': self._set_package_details(packages, carrier, ship_from, ship_to, cod_info, ship=True, is_return=is_return),
                    'Shipper': self._get_ship_data_from_partner(shipper, self.shipper_number),
                    'ShipFrom': self._get_ship_data_from_partner(ship_from),
                    'ShipTo': self._get_ship_data_from_partner(ship_to),
                    'Service': {
                        'Code': service_type,
                    },
                    'NumOfPiecesInShipment': int(shipment_info.get('total_qty')) if service_type == '96' else None,
                    'ShipmentServiceOptions': shipment_service_options if shipment_service_options else None,
                    'ShipmentRatingOptions': {
                        'NegotiatedRatesIndicator': '1',
                    },
                    'PaymentInformation': {
                        'ShipmentCharge': payment_info,
                    }
                },
            },
        }
        # Shipments from US to CA or PR require extra info
        if ship_from.country_id.code == 'US' and ship_to.country_id.code in ['CA', 'PR']:
            request['ShipmentRequest']['Shipment']['InvoiceLineTotal'] = {
                'CurrencyCode': shipment_info.get('itl_currency_code'),
                'MonetaryValue': shipment_info.get('ilt_monetary_value'),
            }
        res = self._send_request(url, 'POST', json=request)
        if res.status_code == 401:
            raise ValidationError(_("Invalid Authentication Information: Please check your credentials and configuration within UPS's system."))
        try:
            res_body = res.json()
        except JSONDecodeError as err:
            self.logger(str(err), f'ups response decode error {url}')
            raise ValidationError(_('Could not decode response'))
        if not res.ok:
            raise ValidationError(self._process_errors(res.json()))
        result = {}
        shipment_result = res_body['ShipmentResponse']['ShipmentResults']
        packs = shipment_result.get('PackageResults', [])
        # get package labels
        if not isinstance(packs, list):
            packs = [packs]
        result['tracking_ref'] = shipment_result['ShipmentIdentificationNumber']
        labels_binary = [(pack['TrackingNumber'], self._save_label(pack['ShippingLabel']['GraphicImage'], label_file_type=label_file_type)) for pack in packs]
        result['label_binary_data'] = labels_binary
        # save international form if in response
        international_form = shipment_result.get('Form', False)
        if international_form:
            result['invoice_binary_data'] = self._save_label(international_form['Image']['GraphicImage'], label_file_type='pdf')
        # Some users are qualified to receive negotiated rates
        if shipment_result.get('NegotiatedRateCharges'):
            charge = shipment_result['NegotiatedRateCharges']['TotalCharge']
        else:
            charge = shipment_result['ShipmentCharges']['TotalCharges']
        result['currency_code'] = charge['CurrencyCode']
        result['price'] = charge['MonetaryValue']
        return result

    def _cancel_shipping(self, shipping_id):
        url = f'/api/shipments/{API_VERSION}/void/cancel/{shipping_id}'
        res = self._send_request(url, 'DELETE')
        if res.status_code == 401:
            raise ValidationError(_("Invalid Authentication Information: Please check your credentials and configuration within UPS's system."))
        try:
            res_body = res.json()
        except JSONDecodeError as err:
            self.logger(str(err), f'ups response decode error {url}')
            raise ValidationError(_('Could not decode response'))
        if not res.ok:
            raise ValidationError(self._process_errors(res.json()))
        return res_body['VoidShipmentResponse']['SummaryResult']['Status']
