# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests
from datetime import datetime
from json.decoder import JSONDecodeError
from requests.exceptions import RequestException

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round, json_float_round

TEST_BASE_URL = 'https://express.api.dhl.com/mydhlapi/test/'
PROD_BASE_URL = 'https://express.api.dhl.com/mydhlapi/'


class DHLProvider:
    def __init__(self, carrier):
        super_carrier = carrier.sudo()
        self.logger = super_carrier.log_xml
        self.base_url = PROD_BASE_URL if super_carrier.prod_environment else TEST_BASE_URL
        if not super_carrier.dhl_api_key:
            raise ValidationError(_("DHL API key is missing, please modify your delivery method settings."))
        if not super_carrier.dhl_api_secret:
            raise ValidationError(_("DHL API secret is missing, please modify your delivery method settings."))
        self.session = requests.Session()
        self.session.auth = (super_carrier.dhl_api_key, super_carrier.dhl_api_secret)

    def _send_request(self, url, method='GET', data=None, json=None):
        url = f'{self.base_url}{url}'

        self.logger(f'{url}\n{method}\n{data}\n{json}', f'dhl request {url}')
        try:
            res = self.session.request(method=method, url=url, data=data, json=json, timeout=15)
            self.logger(f'{res.status_code} {res.text}', f'dhl response {url}')
        except RequestException as err:
            self.logger(str(err), f'dhl response {url}')
            raise ValidationError(_('Something went wrong, please try again later!!')) from None
        return res

    def _process_errors(self, res_body):
        err_msgs = [' '.join([res_body.get('title', ''), res_body.get('detail', '')])]
        if res_body.get('additionalDetails'):
            for detail in res_body['additionalDetails']:
                err_msgs.append(detail)
        for reason in res_body.get('reasons', []):
            err_msgs.append(reason['msg'])
        return '\n'.join(err_msgs)

    def _check_required_value(self, carrier, recipient, shipper, order=False, picking=False):
        carrier = carrier.sudo()
        recipient_required_field = ['city', 'zip', 'phone', 'country_id']
        if not carrier.dhl_account_number:
            return _("DHL account number is missing, please modify your delivery method settings.")

        # The street isn't required if we compute the rate with a partial delivery address in the
        # express checkout flow.
        if not recipient.street and not recipient.street2 and not recipient._context.get(
            'express_checkout_partial_delivery_address', False
        ):
            recipient_required_field.append('street')
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The address of the customer is missing or wrong (Missing field(s) :\n %s)", ", ".join(res).replace("_id", ""))

        shipper_required_field = ['city', 'zip', 'phone', 'country_id']
        if not shipper.street2:
            shipper_required_field.append('street')

        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The address of your company warehouse is missing or wrong (Missing field(s) :\n %s)", ", ".join(res).replace("_id", ""))

        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            error_lines = order.order_line._get_invalid_delivery_weight_lines()
            if error_lines:
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s", ", ".join(error_lines.product_id.mapped('name')))
        return ''

    def _get_from_vals(self, warehouse_partner_id):
        return {
            'countryCode': warehouse_partner_id.country_id.code,
            'postalCode': warehouse_partner_id.zip,
            'cityName': warehouse_partner_id.city,
        }

    def _get_to_vals(self, partner_id):
        return {
            'countryCode': partner_id.country_id.code,
            'postalCode': partner_id.zip,
            'cityName': partner_id.city,
        }

    def _get_package_vals(self, carrier, packages):
        return [{
            'weight': carrier._dhl_convert_weight(p['weight']),
            'dimensions': {
                'length': p['dimension']['length'],
                'width': p['dimension']['width'],
                'height': p['dimension']['height'],
            }
        } for p in packages]

    def _get_dutiable_vals(self, total_value, currency_name):
        return [{
            'typeCode': 'declaredValue',
            'value': total_value,
            'currency': currency_name,
        }]

    def _get_rates(self, rating_request):
        url = 'rates'
        res = self._send_request(url, method='POST', json=rating_request)
        try:
            res_body = res.json()
        except JSONDecodeError as err:
            self.logger(str(err), f'dhl response decoding error {url}')
            raise ValidationError(_('Could not decode the response from DHL.')) from None
        if not res.ok:
            raise ValidationError(self._process_errors(res_body)) from None
        return res_body

    def _get_billing_vals(self, shipper_account, payment_type):
        return [{
            'typeCode': payment_type,
            'number': shipper_account,
        }]

    def _get_consignee_vals(self, partner_id):
        consignee_dict = {
            'postalAddress': {
                'postalCode': partner_id.zip,
                'cityName': partner_id.city,
                'countryCode': partner_id.country_id.code,
                'addressLine1': partner_id.street or partner_id.street2,
            },
            'contactInformation': {
                'phone': partner_id.phone,
                'companyName': partner_id.commercial_company_name or partner_id.name,
                'fullName': partner_id.name,
            }
        }
        if partner_id.email:
            consignee_dict['contactInformation']['email'] = partner_id.email
        if partner_id.street2:
            consignee_dict['postalAddress']['addressLine2'] = partner_id.street2
        if partner_id.state_id:
            consignee_dict['postalAddress']['provinceName'] = partner_id.state_id.name
            consignee_dict['postalAddress']['provinceCode'] = partner_id.state_id.code
        return consignee_dict

    def _get_shipper_vals(self, company_partner_id, warehouse_partner_id):
        shipper_dict = {
            'postalAddress': {
                'postalCode': warehouse_partner_id.zip,
                'cityName': warehouse_partner_id.city,
                'countryCode': warehouse_partner_id.country_id.code,
                'addressLine1': warehouse_partner_id.street or warehouse_partner_id.street2,
            },
            'contactInformation': {
                'phone': company_partner_id.phone,
                'companyName': company_partner_id.commercial_company_name or company_partner_id.name,
                'fullName': company_partner_id.name,
            },
        }
        if company_partner_id.email:
            shipper_dict['contactInformation']['email'] = company_partner_id.email
        if warehouse_partner_id.street2:
            shipper_dict['postalAddress']['addressLine2'] = warehouse_partner_id.street2
        if warehouse_partner_id.state_id:
            shipper_dict['postalAddress']['provinceName'] = warehouse_partner_id.state_id.name
            shipper_dict['postalAddress']['provinceCode'] = warehouse_partner_id.state_id.code
        return shipper_dict

    def _get_export_declaration_vals(self, carrier, picking, is_return=False):
        export_declaration = {}
        export_lines = []
        move_lines = picking.move_line_ids.filtered(lambda line: line.product_id.type in ['product', 'consu'])
        for sequence, line in enumerate(move_lines, start=1):
            if line.move_id.sale_line_id:
                unit_quantity = line.product_uom_id._compute_quantity(line.quantity, line.move_id.sale_line_id.product_uom)
            else:
                unit_quantity = line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0, rounding_method='HALF-UP'))
            item = {
                'number': sequence,
                'description': line.product_id.name,
                'price': json_float_round(line.sale_price / rounded_qty, 3),
                'quantity': {
                    'value': int(rounded_qty),
                    'unitOfMeasurement': 'PCS'
                },
                'weight': {
                    'netValue': carrier._dhl_convert_weight(line.product_id.weight),
                    'grossValue': carrier._dhl_convert_weight(line.product_id.weight),
                },
                'manufacturerCountry': line.picking_id.picking_type_id.warehouse_id.partner_id.country_id.code
            }
            if line.product_id.hs_code:
                item['commodityCodes'] = [{'typeCode': 'inbound', 'value': line.product_id.hs_code}]
            export_lines.append(item)
        export_declaration['lineItems'] = export_lines
        export_declaration['invoice'] = {
            'number': carrier.env['ir.sequence'].sudo().next_by_code('delivery_dhl_rest.commercial_invoice'),
            'date': datetime.today().strftime('%Y-%m-%d'),
        }
        if is_return:
            export_declaration['exportReasonType'] = 'return'
        if picking.sale_id.client_order_ref:
            export_declaration['recipientReference'] = picking.sale_id.client_order_ref
        return export_declaration

    def _get_shipment_vals(self, picking):
        packages = picking.carrier_id._get_picking_packages(picking)
        return [{
            'weight': picking.carrier_id._dhl_convert_weight(package['weight']),
            'dimensions': {
                'length': package.get('dimension', {}).get('length', 0),
                'width': package.get('dimension', {}).get('width', 0),
                'height': package.get('dimension', {}).get('height', 0),
            },
            'description': package.get('name', '')
        } for package in packages]

    def _get_insurance_vals(self, insurance_percentage, total_value, currency_name):
        return {
            'serviceCode': 'II',
            'value': float_round(total_value * insurance_percentage / 100, precision_digits=3),
            'currency': currency_name,
        }

    def _send_shipment(self, shipment_request):
        url = 'shipments'
        res = self._send_request(url, method='POST', json=shipment_request)
        try:
            res_body = res.json()
        except JSONDecodeError as err:
            self.logger(str(err), f'dhl response decoding error {url}')
            raise ValidationError(_('Could not decode the response from DHL.')) from None
        if not res.ok:
            raise ValidationError(self._process_errors(res_body)) from None
        return res_body
