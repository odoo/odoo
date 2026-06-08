# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import re
import time
import zipfile

import requests
from requests.exceptions import RequestException

from odoo.tools.urls import urljoin as url_join

SINVOICE_API_URL = 'https://api-vinvoice.viettel.vn/services/einvoiceapplication/api/'
SINVOICE_AUTH_URL = 'https://api-vinvoice.viettel.vn/auth/login'
SINVOICE_TIMEOUT = 60  # They recommend between 60 and 90 seconds, but 60s is already quite long.
SINVOICE_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB — generous for invoice ZIP/XML files.


class SInvoiceService:
    """Service class for interacting with the Viettel SInvoice API."""

    def __init__(self, access_token, vat, env):
        self._active = False
        self.access_token = access_token
        self.vat = vat
        self.env = env

    def __enter__(self):
        self._active = True
        self.session = requests.Session()
        self.session.cookies.set('access_token', self.access_token)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._active = False
        self.access_token = None
        self.session.close()
        self.session = None

    @classmethod
    def get_access_token(cls, username, password, env):
        """
        Request a new access token from the SInvoice auth endpoint.
        :return: (token_data_dict, error_message).
        """
        try:
            with requests.Session() as session:
                response = session.post(
                    SINVOICE_AUTH_URL,
                    json={'username': username, 'password': password},
                    timeout=SINVOICE_TIMEOUT,
                )
                resp_json = response.json()
                if resp_json.get('code') or resp_json.get('error'):
                    data = resp_json.get('data') or resp_json.get('error')
                    return {}, env._('Error when contacting SInvoice: %s.', data)
                return resp_json, None
        except (RequestException, ValueError) as err:
            return {}, env._('Something went wrong, please try again later: %s', err)

    def _send_request(self, method, endpoint, json_data=None, params=None, headers=None):
        """
        Send an authenticated request to the SInvoice API.
        :return: (response_dict, error_message).
        """
        url = url_join(SINVOICE_API_URL, endpoint)
        try:
            response = self.session.request(
                method, url,
                json=json_data,
                params=params,
                headers=headers,
                timeout=SINVOICE_TIMEOUT,
            )
            resp_json = response.json()
            if resp_json.get('code') or resp_json.get('error'):
                data = resp_json.get('data') or resp_json.get('error')
                return resp_json, self.env._('Error when contacting SInvoice: %s.', data)
            return resp_json, None
        except (RequestException, ValueError) as err:
            return {}, self.env._('Something went wrong, please try again later: %s', err)

    # -------------------------------------------------------------------------
    # INVOICE / DOCUMENT OPERATIONS
    # -------------------------------------------------------------------------

    def create_invoice(self, json_data):
        """
        Create an invoice/document on SInvoice.
        :return: (result_dict, error_message).
        """
        resp, error = self._send_request(
            method='POST',
            endpoint=f'InvoiceAPI/InvoiceWS/createInvoice/{self.vat}',
            json_data=json_data,
        )
        if error:
            return {}, error
        return resp.get('result', {}), None

    def lookup_invoice(self, transaction_uuid):
        """
        Look up a document by its transaction UUID.
        :return: (response_dict, error_message).
        """
        return self._send_request(
            method='POST',
            endpoint='InvoiceAPI/InvoiceWS/searchInvoiceByTransactionUuid',
            params={
                'supplierTaxCode': self.vat,
                'transactionUuid': transaction_uuid,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded;'},
        )

    def cancel_invoice(self, template_code, invoice_no, issue_date_ms, reason,
                       agreement_desc=None, agreement_date_ms=None):
        """
        Cancel an invoice on SInvoice.
        :return: (response_dict, error_message).
        """
        return self._send_request(
            method='POST',
            endpoint='InvoiceAPI/InvoiceWS/cancelTransactionInvoice',
            params={
                'supplierTaxCode': self.vat,
                'templateCode': template_code,
                'invoiceNo': invoice_no,
                'strIssueDate': issue_date_ms,
                'additionalReferenceDesc': agreement_desc,
                'additionalReferenceDate': agreement_date_ms,
                'reasonDelete': reason,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded;'},
        )

    def update_payment_status(self, invoice_no, issue_date_ms, template_code):
        """
        Mark an invoice as paid on SInvoice.
        :return: (response_dict, error_message).
        """
        return self._send_request(
            method='POST',
            endpoint='InvoiceAPI/InvoiceWS/updatePaymentStatus',
            params={
                'supplierTaxCode': self.vat,
                'invoiceNo': invoice_no,
                'strIssueDate': issue_date_ms,
                'templateCode': template_code,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded;'},
        )

    def cancel_payment_status(self, invoice_no, issue_date_ms):
        """
        Mark an invoice as unpaid on SInvoice.
        :return: (response_dict, error_message).
        """
        return self._send_request(
            method='POST',
            endpoint='InvoiceAPI/InvoiceWS/cancelPaymentStatus',
            params={
                'supplierTaxCode': self.vat,
                'invoiceNo': invoice_no,
                'strIssueDate': issue_date_ms,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded;'},
        )

    def get_invoice_file(self, template_code, invoice_no, file_type):
        """
        Fetch the PDF or ZIP file representation of a document.
        Retries a few times since files may not be immediately available.
        :return: (file_data_dict, error_message).
        """
        file_data, error = self._send_request(
            method='POST',
            endpoint='InvoiceAPI/InvoiceUtilsWS/getInvoiceRepresentationFile',
            json_data={
                'supplierTaxCode': self.vat,
                'templateCode': template_code,
                'invoiceNo': invoice_no,
                'fileType': file_type,
            },
        )
        if error:
            return {}, error

        # Sometimes documents are not immediately available after creation.
        # Retry up to 3 times with short delays.
        threshold = 1
        while not file_data.get('fileToBytes') and threshold < 3:
            time.sleep(0.125 * threshold)
            file_data, error = self._send_request(
                method='POST',
                endpoint='InvoiceAPI/InvoiceUtilsWS/getInvoiceRepresentationFile',
                json_data={
                    'supplierTaxCode': self.vat,
                    'templateCode': template_code,
                    'invoiceNo': invoice_no,
                    'fileType': file_type,
                },
            )
            if error:
                return {}, error
            threshold += 1

        return file_data, None

    def get_all_invoice_templates(self):
        """
        Fetch all available invoice symbols/templates for this VAT number.
        :return: (templates_list, error_message).
        """
        resp, error = self._send_request(
            method='POST',
            endpoint='InvoiceAPI/InvoiceUtilsWS/getAllInvoiceTemplates',
            json_data={
                'taxCode': self.vat,
                'invoiceType': 'all',
            },
            headers={
                'Content-Type': 'application/json',
            },
        )
        if error:
            return [], error
        return resp.get('template', []), None

    def get_custom_fields(self, tax_code, template_code):
        """
        Fetch the template-specific custom fields for a given VAT and template code.
        :return: (custom_fields_list, error_message).
        """
        resp, error = self._send_request(
            method='GET',
            endpoint='InvoiceAPI/InvoiceWS/getCustomFields',
            params={'taxCode': tax_code, 'templateCode': template_code},
        )
        if error:
            return [], error
        # This endpoint uses 'errorCode'/'description' instead of 'code'/'error'
        if resp.get('errorCode'):
            return [], self.env._('Error fetching custom fields from SInvoice: %s', resp.get('description', ''))
        return resp.get('customFields', []), None

    # -------------------------------------------------------------------------
    # FILE EXTRACTION HELPERS
    # -------------------------------------------------------------------------

    def extract_xml_from_zip(self, zip_bytes):
        """
        Extract the XML file from SInvoice's nested ZIP format.
        :return: (file_dict, error_message).
        """
        try:
            # SInvoice returns a zip containing another zip, which contains the xsl + xml files.
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
                outer_entry = zip_file.infolist()[0]
                if outer_entry.file_size > SINVOICE_MAX_FILE_SIZE:
                    return {}, self.env._('SInvoice ZIP entry exceeds maximum allowed file size.')
                inner_zip_bytes = zip_file.read(outer_entry)
                with zipfile.ZipFile(io.BytesIO(inner_zip_bytes)) as inner_zip:
                    for file in inner_zip.infolist():
                        if file.filename.endswith('.xml'):
                            if file.file_size > SINVOICE_MAX_FILE_SIZE:
                                return {}, self.env._('SInvoice ZIP entry exceeds maximum allowed file size.')
                            return {
                                'name': file.filename,
                                'mimetype': 'application/xml',
                                'raw': inner_zip.read(file),
                            }, None
            return {}, self.env._('No XML file found in the SInvoice ZIP response.')
        except Exception as err:  # noqa: BLE001
            return {}, self.env._('Failed to extract XML from SInvoice ZIP: %s', err)

    # -------------------------------------------------------------------------
    # FORMATTING UTILITIES
    # -------------------------------------------------------------------------

    @staticmethod
    def format_date(date):
        """
        All SInvoice APIs use the same time format: seconds since Unix epoch formatted as milliseconds.
        The millisecond digits are always 000 since they are not currently used by the system.
        """
        return int(date.timestamp()) * 1000 if date else 0

    @staticmethod
    def format_phone_number(number):
        """
        Format a phone number for SInvoice: digits only, replacing + with 00.
        """
        number = number.replace('+', '00')
        return re.sub(r'[^0-9]+', '', number)
