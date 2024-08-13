# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode, b64encode
import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import dateutil.parser
from lxml import etree
import requests

from odoo import _, release
from odoo.tools import cleanup_xml_node


_logger = logging.getLogger(__name__)


XML_NAMESPACES = {
    'api': 'http://schemas.nav.gov.hu/OSA/3.0/api',
    'common': 'http://schemas.nav.gov.hu/NTCA/1.0/common',
    'base': 'http://schemas.nav.gov.hu/OSA/3.0/base',
    'data': 'http://schemas.nav.gov.hu/OSA/3.0/data',
}


def format_bool(value):
    return 'true' if value else 'false'


def format_timestamp(value):
    return value.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def decrypt_aes128(key, encrypted_token):
    """ Decrypt AES-128-ECB encrypted bytes.
    :param key bytes: the 128-bit key
    :param encrypted_token bytes: the bytes to decrypt
    :return: the decrypted bytes
    """
    decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    decrypted_token = decryptor.update(encrypted_token) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    unpadded_token = unpadder.update(decrypted_token) + unpadder.finalize()
    return unpadded_token


class L10nHuEdiConnectionError(Exception):
    def __init__(self, errors, code=None):
        if not isinstance(errors, list):
            errors = [errors]
        self.errors = errors
        self.code = code
        super().__init__('\n'.join(errors))


class L10nHuEdiConnection:
    def __init__(self, env):
        """ Methods to call NAV API endpoints.
        Use this as a context manager (`with L10nHuEdiConnection(...) as connection`)
        to ensure the TCP connection is closed when you are finished calling endpoints.

        :param env: the Odoo environment
        """
        self.env = env
        self.session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def do_token_exchange(self, credentials):
        """ Request a token for invoice submission.

        :param credentials: a dictionary
            {
                'vat': str,
                'mode': 'production' || 'test',
                'username': str,
                'password': str,
                'signature_key': str,
                'replacement_key': str
            }
        :return: a dictionary {'token': str, 'token_validity_to': datetime}
        :raise: L10nHuEdiConnectionError
        """
        if credentials['mode'] == 'demo':
            return {'token': 'token', 'token_validity_to': datetime.utcnow() + timedelta(minutes=5)}

        template_values = self._get_header_values(credentials)
        request_data = self.env['ir.qweb']._render('l10n_hu_edi.token_exchange_request', template_values)
        request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

        response_xml = self._call_nav_endpoint(credentials['mode'], 'tokenExchange', request_data)
        self._parse_error_response(response_xml)

        encrypted_token = response_xml.findtext('api:encodedExchangeToken', namespaces=XML_NAMESPACES)
        token_validity_to = response_xml.findtext('api:tokenValidityTo', namespaces=XML_NAMESPACES)
        try:
            # Convert into a naive UTC datetime, since Odoo can't store timezone-aware datetimes
            token_validity_to = dateutil.parser.isoparse(token_validity_to).astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            _logger.warning('Could not parse token validity end timestamp!')
            token_validity_to = datetime.utcnow() + timedelta(minutes=5)

        if not encrypted_token:
            raise L10nHuEdiConnectionError(_('Missing token in response from NAV.'))

        try:
            token = decrypt_aes128(credentials['replacement_key'].encode(), b64decode(encrypted_token.encode())).decode()
        except ValueError as e:
            raise L10nHuEdiConnectionError(_('Error during decryption of ExchangeToken.')) from e

        return {'token': token, 'token_validity_to': token_validity_to}

    def do_manage_invoice(self, credentials, token, invoice_operations):
        """ Submit one or more invoices.

        :param token: a token obtained via `do_token_exchange`
        :param invoice_operations: a list of dictionaries:
            {
                'index': <index given to invoice>,
                'operation': 'CREATE' or 'MODIFY',
                'invoice_data': <XML data of the invoice as bytes>
            }
        :return str: The transaction code issued by NAV.
        :raise: L10nHuEdiConnectionError, with code='timeout' if a timeout occurred.
        """
        if credentials['mode'] == 'demo':
            return secrets.token_hex(8).upper()

        template_values = {
            'exchangeToken': token,
            'compressedContent': False,
            'invoices': [],
        }
        invoice_hashes = []
        for invoice_operation in invoice_operations:
            invoice_data_b64 = b64encode(invoice_operation['invoice_data']).decode('utf-8')
            template_values['invoices'].append({
                'index': invoice_operation['index'],
                'invoiceOperation': invoice_operation['operation'],
                'invoiceData': invoice_data_b64,
            })
            invoice_hashes.append(self._calculate_invoice_hash(invoice_operation['operation'] + invoice_data_b64))

        template_values.update(self._get_header_values(credentials, invoice_hashs=invoice_hashes))

        request_data = self.env['ir.qweb']._render('l10n_hu_edi.manage_invoice_request', template_values)
        request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

        response_xml = self._call_nav_endpoint(credentials['mode'], 'manageInvoice', request_data, timeout=60)
        self._parse_error_response(response_xml)

        transaction_code = response_xml.findtext('api:transactionId', namespaces=XML_NAMESPACES)
        if not transaction_code:
            raise L10nHuEdiConnectionError(_('Invoice Upload failed: NAV did not return a Transaction ID.'))

        return transaction_code

    def do_query_transaction_status(self, credentials, transaction_code, return_original_request=False):
        """ Query the status of a transaction.

        :param transaction_code: the code of the transaction to query
        :param return_original_request: whether to request the submitted invoice XML.
        :return: a list of dicts {'index': str, 'invoice_status': str, 'business_validation_messages', 'technical_validation_messages'}
        :raise: L10nHuEdiConnectionError
        """
        if credentials['mode'] == 'demo':
            invoices = self.env['account.move'].search([('l10n_hu_edi_transaction_code', '=', transaction_code)])
            if any(m.l10n_hu_edi_state.startswith('cancel') for m in invoices):
                return {
                    'processing_results': [
                        {
                            'index': str(i + 1),
                            'invoice_status': 'DONE',
                            'business_validation_messages': [{
                                'validation_result_code': 'INFO',
                                'validation_error_code': 'INFO_SINGLE_INVOICE_ANNULMENT',
                                'message': 'Egyedi számla technikai érvénytelenítése',
                            }],
                            'technical_validation_messages': [],
                        }
                        for i in range(len(invoices))
                    ],
                    'annulment_status': 'VERIFICATION_DONE',
                }
            else:
                return {
                    'processing_results': [
                        {
                            'index': str(i + 1),
                            'invoice_status': 'DONE',
                            'business_validation_messages': [],
                            'technical_validation_messages': [],
                        }
                        for i in range(len(invoices))
                    ],
                    'annulment_status': None,
                }

        template_values = {
            **self._get_header_values(credentials),
            'transactionId': transaction_code,
            'returnOriginalRequest': return_original_request,
        }
        request_data = self.env['ir.qweb']._render('l10n_hu_edi.query_transaction_status_request', template_values)
        request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

        response_xml = self._call_nav_endpoint(credentials['mode'], 'queryTransactionStatus', request_data)
        self._parse_error_response(response_xml)

        results = {
            'processing_results': [],
            'annulment_status': response_xml.findtext('api:processingResults/api:annulmentData/api:annulmentVerificationStatus', namespaces=XML_NAMESPACES),
        }
        for processing_result_xml in response_xml.iterfind('api:processingResults/api:processingResult', namespaces=XML_NAMESPACES):
            processing_result = {
                'index': processing_result_xml.findtext('api:index', namespaces=XML_NAMESPACES),
                'invoice_status': processing_result_xml.findtext('api:invoiceStatus', namespaces=XML_NAMESPACES),
                'business_validation_messages': [],
                'technical_validation_messages': [],
            }
            for message_xml in processing_result_xml.iterfind('api:businessValidationMessages', namespaces=XML_NAMESPACES):
                processing_result['business_validation_messages'].append({
                    'validation_result_code': message_xml.findtext('api:validationResultCode', namespaces=XML_NAMESPACES),
                    'validation_error_code': message_xml.findtext('api:validationErrorCode', namespaces=XML_NAMESPACES),
                    'message': message_xml.findtext('api:message', namespaces=XML_NAMESPACES),
                })
            for message_xml in processing_result_xml.iterfind('api:technicalValidationMessages', namespaces=XML_NAMESPACES):
                processing_result['technical_validation_messages'].append({
                    'validation_result_code': message_xml.findtext('api:validationResultCode', namespaces=XML_NAMESPACES),
                    'validation_error_code': message_xml.findtext('api:validationErrorCode', namespaces=XML_NAMESPACES),
                    'message': message_xml.findtext('api:message', namespaces=XML_NAMESPACES),
                })
            if return_original_request:
                try:
                    original_file = b64decode(processing_result_xml.findtext('api:originalRequest', namespaces=XML_NAMESPACES))
                    original_xml = etree.fromstring(original_file)
                except binascii.Error as e:
                    raise L10nHuEdiConnectionError(str(e)) from e
                except etree.ParserError as e:
                    raise L10nHuEdiConnectionError(str(e)) from e

                processing_result.update({
                    'original_file': original_file.decode(),
                    'original_xml': original_xml,
                })

            results['processing_results'].append(processing_result)

        return results

    def do_query_transaction_list(self, credentials, datetime_from, datetime_to, page=1):
        """ Query the transactions that were submitted in a given time interval.

        :param datetime_from: start of the time interval to query
        :param datetime_to: end of the time interval to query
        :return: a dict {'transaction_codes': list[str], 'available_pages': int}
        :raise: L10nHuEdiConnectionError
        """
        if credentials['mode'] == 'demo':
            return {"transactions": [], "available_pages": 1}

        template_values = {
            **self._get_header_values(credentials),
            'page': page,
            'dateTimeFrom': format_timestamp(datetime_from),
            'dateTimeTo': format_timestamp(datetime_to),
        }
        request_data = self.env['ir.qweb']._render('l10n_hu_edi.query_transaction_list_request', template_values)
        request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

        response_xml = self._call_nav_endpoint(credentials['mode'], 'queryTransactionList', request_data)
        self._parse_error_response(response_xml)

        available_pages = response_xml.findtext('api:transactionListResult/api:availablePage', namespaces=XML_NAMESPACES)
        try:
            available_pages = int(available_pages)
        except ValueError:
            available_pages = 1

        transactions = []
        for transaction_xml in response_xml.iterfind('api:transactionListResult/api:transaction', namespaces=XML_NAMESPACES):
            try:
                send_time = datetime.fromisoformat(transaction_xml.findtext('api:insDate', namespaces=XML_NAMESPACES).replace('Z', ''))
            except ValueError as e:
                raise L10nHuEdiConnectionError(_('Could not parse time of previous transaction')) from e
            transactions.append({
                'transaction_code': transaction_xml.findtext('api:transactionId', namespaces=XML_NAMESPACES),
                'annulment': transaction_xml.findtext('api:technicalAnnulment', namespaces=XML_NAMESPACES) == 'true',
                'username': transaction_xml.findtext('api:insCusUser', namespaces=XML_NAMESPACES),
                'source': transaction_xml.findtext('api:source', namespaces=XML_NAMESPACES),
                'send_time': send_time,
            })

        return {"transactions": transactions, "available_pages": available_pages}

    def do_manage_annulment(self, credentials, token, annulment_operations):
        """ Request technical annulment of one or more invoices.

        :param token: a token obtained via `do_token_exchange`
        :param annulment_operations: a list of dictionaries:
            {
                'index': <index given to invoice>,
                'annulmentReference': the name of the invoice to annul,
                'annulmentCode': one of ('ERRATIC_DATA', 'ERRATIC_INVOICE_NUMBER', 'ERRATIC_INVOICE_ISSUE_DATE', 'ERRATIC_ELECTRONIC_HASH_VALUE'),
                'annulmentReason': a plain-text explanation of the reason for annulment,
            }
        :return str: The transaction code issued by NAV.
        :raise: L10nHuEdiConnectionError, with code='timeout' if a timeout occurred.
        """
        if credentials['mode'] == 'demo':
            return secrets.token_hex(8).upper()

        template_values = {
            'exchangeToken': token,
            'annulments': []
        }

        annulment_hashes = []
        for annulment_operation in annulment_operations:
            annulment_operation['annulmentTimestamp'] = format_timestamp(datetime.utcnow())
            annulment_data = self.env['ir.qweb']._render('l10n_hu_edi.invoice_annulment', annulment_operation)
            annulment_data_b64 = b64encode(annulment_data.encode()).decode('utf-8')
            template_values['annulments'].append({
                'index': annulment_operation['index'],
                'annulmentOperation': 'ANNUL',
                'invoiceAnnulment': annulment_data_b64,
            })
            annulment_hashes.append(self._calculate_invoice_hash('ANNUL' + annulment_data_b64))

        template_values.update(self._get_header_values(credentials, invoice_hashs=annulment_hashes))

        request_data = self.env['ir.qweb']._render('l10n_hu_edi.manage_annulment_request', template_values)
        request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

        response_xml = self._call_nav_endpoint(credentials['mode'], 'manageAnnulment', request_data, timeout=60)
        self._parse_error_response(response_xml)

        transaction_code = response_xml.findtext('api:transactionId', namespaces=XML_NAMESPACES)
        if not transaction_code:
            raise L10nHuEdiConnectionError(_('Invoice Upload failed: NAV did not return a Transaction ID.'))

        return transaction_code

    # === Helpers: XML generation === #

    def _get_header_values(self, credentials, invoice_hashs=None):
        timestamp = datetime.utcnow()
        request_id = 'ODOO' + secrets.token_hex(13)
        request_signature = self._calculate_request_signature(credentials['signature_key'], request_id, timestamp, invoice_hashs=invoice_hashs)
        odoo_version = release.version
        module_version = self.env['ir.module.module'].get_module_info('l10n_hu_edi').get('version').replace('saas~', '').replace('.', '')

        return {
            'requestId': request_id,
            'timestamp': format_timestamp(timestamp),
            'login': credentials['username'],
            'passwordHash': self._calculate_password_hash(credentials['password']),
            'taxNumber': credentials['vat'][:8],
            'requestSignature': request_signature,
            'softwareId': f'BE477472701-{module_version}'[:18],
            'softwareName': 'Odoo Enterprise',
            'softwareOperation': 'ONLINE_SERVICE',
            'softwareMainVersion': odoo_version,
            'softwareDevName': 'Odoo SA',
            'softwareDevContact': 'andu@odoo.com',
            'softwareDevCountryCode': 'BE',
            'softwareDevTaxNumber': '477472701',
            'format_bool': format_bool,
        }

    def _calculate_password_hash(self, password):
        return hashlib.sha512(password.encode()).hexdigest().upper()

    def _calculate_invoice_hash(self, value):
        return hashlib.sha3_512(value.encode()).hexdigest().upper()

    def _calculate_request_signature(self, key_sign, reqid, reqdate, invoice_hashs=None):
        strings = [reqid, reqdate.strftime('%Y%m%d%H%M%S'), key_sign]

        # merge the invoice CRCs if we got
        if invoice_hashs:
            strings += invoice_hashs

        # return back the uppered hexdigest
        return self._calculate_invoice_hash(''.join(strings))

    # === Helpers: HTTP Post === #

    def _call_nav_endpoint(self, mode, service, data, timeout=20):
        if mode == 'production':
            url = 'https://api.onlineszamla.nav.gov.hu/invoiceService/v3/'
        elif mode == 'test':
            url = 'https://api-test.onlineszamla.nav.gov.hu/invoiceService/v3/'
        else:
            raise L10nHuEdiConnectionError(_('Mode should be Production or Test!'))

        headers = {'content-type': 'application/xml', 'accept': 'application/xml'}
        try:
            response_object = self.session.post(f'{url}{service}', data=data, headers=headers, timeout=timeout)
        except requests.Timeout as e:
            raise L10nHuEdiConnectionError(_('Connection to NAV servers timed out.'), code='timeout') from e
        except requests.RequestException as e:
            raise L10nHuEdiConnectionError(str(e)) from e

        try:
            response_xml = etree.fromstring(response_object.text.encode())
        except etree.ParseError as e:
            raise L10nHuEdiConnectionError(_('Invalid NAV response!')) from e

        return response_xml

    # === Helpers: Response parsing === #

    def _parse_error_response(self, response_xml):
        error_code = response_xml.findtext('common:result/common:errorCode', namespaces=XML_NAMESPACES)
        message = response_xml.findtext('common:result/common:message', namespaces=XML_NAMESPACES)
        if error_code:
            errors = [f'{error_code}: {message}']
            for message_xml in response_xml.iterfind('api:technicalValidationMessages', namespaces=XML_NAMESPACES):
                message = message_xml.findtext('api:message', namespaces=XML_NAMESPACES)
                error_code = message_xml.findtext('api:validationErrorCode', namespaces=XML_NAMESPACES)
                errors.append(f'{error_code}: {message}')

            raise L10nHuEdiConnectionError(errors)
