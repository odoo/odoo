# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import re
import requests
from json.decoder import JSONDecodeError
from requests.exceptions import RequestException

from odoo import _
from odoo.exceptions import UserError

TEST_BASE_URL = 'https://apis-tem.usps.com/'
PROD_BASE_URL = 'https://apis.usps.com/'
TOKEN_TYPE = 'Bearer'
API_VERSION = 'v3'
# This re should match postcodes like 12345 and 12345-6789
ZIP_ZIP4 = re.compile('^[0-9]{5}(-[0-9]{4})?$')


def split_zip(zipcode):
    '''If zipcode is a ZIP+4, split it into two parts.
       Else leave it unchanged '''
    if ZIP_ZIP4.match(zipcode) and '-' in zipcode:
        return zipcode.split('-')
    else:
        return [zipcode, '']


class USPSRequest:

    def __init__(self, carrier):
        super_carrier = carrier.sudo()
        self.base_url = PROD_BASE_URL if carrier.prod_environment else TEST_BASE_URL
        self.logger = carrier.log_xml
        self.client_id = super_carrier.usps_api_key
        self.client_secret = super_carrier.usps_api_secret
        self.eps_account_number = super_carrier.usps_eps_account_number
        self.crid = super_carrier.usps_crid
        self.mid = super_carrier.usps_mid
        self.manifest_mid = super_carrier.usps_manifest_mid
        self.access_token = super_carrier.usps_access_token
        self.payment_token = super_carrier.usps_payment_token
        self.carrier = carrier
        self.session = requests.Session()

    def _send_request(self, url, method='GET', data=None, json=None, headers=None, attach_payment_token=False, auth=None):
        url = f'{self.base_url}{url}'

        def _request_call(req_headers):
            if self.access_token and not req_headers:
                req_headers = {
                    'Authorization': f'{TOKEN_TYPE} {self.access_token}'
                }
            if attach_payment_token:
                if not req_headers:
                    req_headers = {}
                req_headers['X-Payment-Authorization-Token'] = self.payment_token
            self.logger(f'{url}\n{method}\n{req_headers}\n{data}\n{json}', f'usps request {url}')
            try:
                self.session.cookies.clear()
                res = self.session.request(method=method, url=url, data=data, json=json, headers=req_headers, auth=auth, cookies=None)
                self.logger(f'{res.status_code}\n{res.text}', f'usps response {url}')
            except RequestException as e:
                self.logger(str(e), f'usps request error {url}')
                raise UserError(str(e))
            return res

        if attach_payment_token:
            self.payment_token = None
            self.payment_token = self._get_new_payment_token()
            self.carrier.sudo().usps_payment_token = self.payment_token

        res = _request_call(headers)
        if res.status_code == 401 and auth is None and 'oauth' not in url:
            self.access_token = None
            self.access_token = self._get_new_access_token()
            self.carrier.sudo().usps_access_token = self.access_token
            res = _request_call(None)
        elif res.status_code == 401 and 'oauth' in url:
            raise UserError(_("Your USPS API Key and Secret are invalid."))

        return res

    def _process_errors(self, res_body):
        err_msgs = []
        if 'error' in res_body:
            err_msgs.append(res_body.get('error', {}).get('message'))
        errors = res_body.get('error', {}).get('errors', [])
        for error in errors:
            msg = f"{error.get('code', '')} {error.get('title', '')}: {error.get('message', '') or error.get('detail', '')}. {error.get('source', '')}"
            err_msgs.append(msg)
        return '\n'.join(err_msgs)

    def _process_authorization_errors(self, res_body):
        return f"{res_body.get('fault', {}).get('detail', {}).get('errorcode', {})} {res_body.get('fault', {}).get('faultstring', {})}"

    def _get_new_access_token(self):
        if not self.client_id or not self.client_secret:
            raise UserError(_("You need to set your USPS API Key and Secret to use this feature."))
        url = 'oauth2/v3/token'
        body = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        res = self._send_request(url, method='POST', json=body)
        try:
            res_body = res.json()
        except JSONDecodeError as err:
            self.logger(str(err), 'usps response decoding error')
            raise UserError(_("Couldn't decode the response from USPS."))
        if not res.ok:
            raise UserError(self._process_authorization_errors(res_body))
        return res_body.get('access_token')

    def _get_new_payment_token(self):
        if not self.crid or not self.mid or not self.manifest_mid or not self.eps_account_number:
            raise UserError(_("You need to set your USPS CRID, MID, Manifest MID and EPS Account Number to use this feature."))
        url = 'payments/v3/payment-authorization'
        body = {
            'roles': [
                {
                    'roleName': 'PAYER',
                    'CRID': self.crid,
                    'MID': self.mid,
                    'manifestMID': self.manifest_mid,
                    'accountType': 'EPS',
                    'accountNumber': self.eps_account_number,
                },
                {
                    'roleName': 'LABEL_OWNER',
                    'CRID': self.crid,
                    'MID': self.mid,
                    'manifestMID': self.manifest_mid,
                    'accountType': 'EPS',
                    'accountNumber': self.eps_account_number,
                }
            ]
        }
        self.carrier._usps_add_extra_data_to_request(body, 'payment_token')
        res = self._send_request(url, method='POST', json=body)
        try:
            res_body = res.json()
        except JSONDecodeError as err:
            self.logger(str(err), 'usps response decoding error')
            raise UserError(_("Couldn't decode the response from USPS."))
        if not res.ok:
            raise UserError(self._process_errors(res_body))
        return res_body.get('paymentAuthorizationToken')

    def check_required_value(self, recipient, delivery_nature, shipper, order=False, picking=False):
        recipient_required_field = ['city', 'zip', 'country_id']
        # The street isn't required if we compute the rate with a partial delivery address in the
        # express checkout flow.
        if not recipient.street and not recipient.street2 and not recipient._context.get(
            'express_checkout_partial_delivery_address', False
        ):
            recipient_required_field.append('street')
        shipper_required_field = ['city', 'zip', 'state_id', 'country_id']
        if not shipper.street and not shipper.street2:
            shipper_required_field.append('street')

        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The address of your company is missing or wrong (Missing field(s) :  \n %s)", ", ".join(res).replace("_id", ""))
        if shipper.country_id.code != 'US':
            return _("Please set country USA in your company address, Service is only available for USA")
        if not ZIP_ZIP4.match(shipper.zip):
            return _("Please enter a valid ZIP code in your Company address")
        if not self._convert_phone_number(shipper.phone):
            return _("Company phone number is invalid. Please insert a US phone number.")
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The recipient address is missing or wrong (Missing field(s) :  \n %s)", ", ".join(res).replace("_id", ""))
        if delivery_nature == 'domestic' and not ZIP_ZIP4.match(recipient.zip):
            return _("Please enter a valid ZIP code in recipient address")
        if recipient.country_id.code == "US" and delivery_nature == 'international':
            return _("USPS International is used only to ship outside of the USA. Please change the delivery method into USPS Domestic.")
        if recipient.country_id.code != "US" and delivery_nature == 'domestic':
            return _("USPS Domestic is used only to ship inside of the USA. Please change the delivery method into USPS International.")
        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            error_lines = order.order_line._get_invalid_delivery_weight_lines()
            if error_lines:
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s", ", ".join(error_lines.product_id.mapped('name')))
        return False

    def _get_rates(self, request_body):
        url_first_token = 'prices' if self.carrier.usps_delivery_nature == 'domestic' else 'international-prices'
        url = f'{url_first_token}/{API_VERSION}/base-rates-list/search'
        res = self._send_request(url, method='POST', json=request_body)
        try:
            res_body = res.json()
        except JSONDecodeError as err:
            self.logger(str(err), 'usps response decoding error')
            raise UserError(_("Couldn't decode the response from USPS."))
        if not res.ok:
            raise UserError(self._process_errors(res_body))
        return res_body

    def _get_shipping_label(self, shipping_data):
        url = 'labels/v3/label' if self.carrier.usps_delivery_nature == 'domestic' else 'international-labels/v3/international-label'
        res = self._send_request(url, method='POST', json=shipping_data, attach_payment_token=True)
        if not res.ok:
            try:
                error_body = res.json()
                raise UserError(self._process_errors(error_body))
            except JSONDecodeError as err:
                self.logger(str(err), 'usps response decoding error')
                raise UserError(_("Couldn't decode the response from USPS.\n%s", res.text))
        multipart_boundary = res.headers['Content-Type'].split('boundary=')[1]
        parts = res.text.split(f'--{multipart_boundary}')
        res_body = {}
        for part in parts:
            if 'name="labelMetadata"' in part:
                label_metadata = part.split('\r\n\r\n')[1]
                res_body['labelMetadata'] = json.loads(label_metadata)
            elif 'name="returnLabelMetadata"' in part:
                return_label_metadata = part.split('\r\n\r\n')[1]
                res_body['returnLabelMetadata'] = json.loads(return_label_metadata)
            elif 'name="labelImage"' in part:
                label_image = part.split('\r\n\r\n')[1]
                res_body['labelImage'] = label_image
            elif 'name="returnLabelImage"' in part:
                return_label_image = part.split('\r\n\r\n')[1]
                res_body['returnLabelImage'] = return_label_image
            elif 'name="receiptImage"' in part:
                receipt_image = part.split('\r\n\r\n')[1]
                res_body['receiptImage'] = receipt_image
        return res_body

    def _cancel_label(self, tracking_number):
        url = f'labels/v3/label/{tracking_number}' if self.carrier.usps_delivery_nature == 'domestic' else f'international-labels/v3/international-label/{tracking_number}'
        res = self._send_request(url, method='DELETE', attach_payment_token=True)
        if not res.ok:
            try:
                error_body = res.json()
                raise UserError(self._process_errors(error_body))
            except JSONDecodeError as err:
                self.logger(str(err), 'usps response decoding error')
                raise UserError(_("Couldn't decode the response from USPS.\n%s", res.text))
        return True

    def _convert_phone_number(self, phone):
        phone_pattern = re.compile(r'''
                # don't match beginning of string, number can start anywhere
                (\d{3})     # area code is 3 digits (e.g. '800')
                \D*         # optional separator is any number of non-digits
                (\d{3})     # trunk is 3 digits (e.g. '555')
                \D*         # optional separator
                (\d{4})     # rest of number is 4 digits (e.g. '1212')
                \D*         # optional separator
                (\d*)       # extension is optional and can be any number of digits
                $           # end of string
                ''', re.VERBOSE)
        match = phone_pattern.search(phone)
        if match:
            return ''.join(str(digits_number) for digits_number in match.groups())
        else:
            return False
