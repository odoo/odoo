# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""DIAN (Direccion de Impuestos y Aduanas Nacionales) SOAP web service client.

Implements the DIAN electronic invoicing web service integration per
DIAN Technical Annex v1.9, supporting both habilitacion (test) and
production environments.

DIAN Service Operations:
- SendBillSync: Synchronous invoice submission and validation
- SendBillAsync: Asynchronous submission (returns ZipKey for polling)
- GetStatus: Check document status by track ID
- GetStatusZip: Check status by ZipKey (from async submission)
- SendTestSetAsync: Submit test set during habilitacion (enablement)
"""

import base64
import io
import logging
import time
import zipfile

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# DIAN WSDL endpoints
DIAN_WSDL = {
    'test': 'https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl',
    'production': 'https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?wsdl',
}

# DIAN response status codes
DIAN_STATUS_OK = 0
DIAN_STATUS_ACCEPTED = 200
DIAN_STATUS_DOC_ACCEPTED = '00'  # Document accepted

# Maximum retries for transient failures
MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 15]  # seconds between retries


class L10nCoEdiDianClient(models.AbstractModel):
    """DIAN web service client for electronic invoicing.

    This abstract model provides methods to interact with DIAN's SOAP web services.
    It handles authentication, request/response processing, ZIP packaging,
    retry logic, and environment switching.
    """
    _name = 'l10n_co_edi.dian.client'
    _description = 'DIAN Web Service Client'

    # =====================================================================
    # Client Construction
    # =====================================================================

    def _get_dian_client(self, company):
        """Create a zeep SOAP client for the DIAN web service.

        :param company: res.company record
        :return: zeep Client wrapper (from odoo.tools.zeep)
        """
        import requests
        from odoo.tools.zeep import Client

        wsdl_url = DIAN_WSDL['test' if company.l10n_co_edi_test_mode else 'production']

        session = requests.Session()
        # DIAN requires TLS 1.2+ with standard cipher suites
        session.headers.update({
            'Content-Type': 'application/soap+xml; charset=utf-8',
        })

        client = Client(
            wsdl_url,
            session=session,
            timeout=30,
            operation_timeout=60,
        )
        return client

    # =====================================================================
    # ZIP Packaging (DIAN requires XML inside a ZIP)
    # =====================================================================

    def _create_dian_zip(self, filename, xml_content):
        """Package XML content into a ZIP file as required by DIAN.

        DIAN expects the signed UBL XML to be wrapped in a ZIP file
        before base64-encoding for transmission.

        :param filename: str — XML filename (e.g., 'ws_SETP990000001.xml')
        :param xml_content: bytes — signed UBL XML
        :return: bytes — base64-encoded ZIP content
        """
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, xml_content)
        zip_bytes = zip_buffer.getvalue()
        return base64.b64encode(zip_bytes)

    # =====================================================================
    # Service Operations
    # =====================================================================

    def _send_bill_sync(self, company, filename, xml_content):
        """Submit an invoice synchronously to DIAN.

        This is the primary submission method. DIAN validates the document
        and returns the result immediately.

        :param company: res.company record
        :param filename: str — XML filename
        :param xml_content: bytes — signed UBL XML
        :return: dict — parsed DIAN response
        """
        content_file = self._create_dian_zip(filename, xml_content)
        client = self._get_dian_client(company)

        for attempt in range(MAX_RETRIES):
            try:
                response = client.service.SendBillSync(
                    fileName=filename.replace('.xml', '.zip'),
                    contentFile=content_file,
                )
                return self._parse_dian_response(response)

            except Exception as e:
                if attempt < MAX_RETRIES - 1 and self._is_transient_error(e):
                    delay = RETRY_DELAYS[attempt]
                    _logger.warning(
                        'DIAN SendBillSync transient error (attempt %d/%d), retrying in %ds: %s',
                        attempt + 1, MAX_RETRIES, delay, str(e),
                    )
                    time.sleep(delay)
                    continue
                raise

    def _send_bill_async(self, company, filename, xml_content):
        """Submit an invoice asynchronously to DIAN.

        Returns a ZipKey that can be used to poll for the result
        using _get_status_zip.

        :param company: res.company record
        :param filename: str — XML filename
        :param xml_content: bytes — signed UBL XML
        :return: dict — parsed response with ZipKey for polling
        """
        content_file = self._create_dian_zip(filename, xml_content)
        client = self._get_dian_client(company)

        for attempt in range(MAX_RETRIES):
            try:
                response = client.service.SendBillAsync(
                    fileName=filename.replace('.xml', '.zip'),
                    contentFile=content_file,
                )
                return self._parse_dian_response(response)

            except Exception as e:
                if attempt < MAX_RETRIES - 1 and self._is_transient_error(e):
                    delay = RETRY_DELAYS[attempt]
                    _logger.warning(
                        'DIAN SendBillAsync transient error (attempt %d/%d), retrying in %ds: %s',
                        attempt + 1, MAX_RETRIES, delay, str(e),
                    )
                    time.sleep(delay)
                    continue
                raise

    def _get_status(self, company, track_id):
        """Check the status of a previously submitted document.

        :param company: res.company record
        :param track_id: str — CUFE/CUDE or track ID from submission
        :return: dict — parsed DIAN response
        """
        client = self._get_dian_client(company)

        for attempt in range(MAX_RETRIES):
            try:
                response = client.service.GetStatus(trackId=track_id)
                return self._parse_dian_response(response)

            except Exception as e:
                if attempt < MAX_RETRIES - 1 and self._is_transient_error(e):
                    delay = RETRY_DELAYS[attempt]
                    _logger.warning(
                        'DIAN GetStatus transient error (attempt %d/%d), retrying in %ds: %s',
                        attempt + 1, MAX_RETRIES, delay, str(e),
                    )
                    time.sleep(delay)
                    continue
                raise

    def _get_status_zip(self, company, zip_key):
        """Check the status of an async submission by ZipKey.

        :param company: res.company record
        :param zip_key: str — ZipKey from SendBillAsync response
        :return: dict — parsed DIAN response
        """
        client = self._get_dian_client(company)

        for attempt in range(MAX_RETRIES):
            try:
                response = client.service.GetStatusZip(zipKey=zip_key)
                return self._parse_dian_response(response)

            except Exception as e:
                if attempt < MAX_RETRIES - 1 and self._is_transient_error(e):
                    delay = RETRY_DELAYS[attempt]
                    _logger.warning(
                        'DIAN GetStatusZip transient error (attempt %d/%d), retrying in %ds: %s',
                        attempt + 1, MAX_RETRIES, delay, str(e),
                    )
                    time.sleep(delay)
                    continue
                raise

    def _send_test_set_async(self, company, filename, xml_content, test_set_id):
        """Submit a document as part of a DIAN test set (habilitacion).

        During the enablement process, documents must be submitted using
        this method instead of SendBillSync/Async.

        :param company: res.company record
        :param filename: str — XML filename
        :param xml_content: bytes — signed UBL XML
        :param test_set_id: str — DIAN test set identifier
        :return: dict — parsed DIAN response
        """
        content_file = self._create_dian_zip(filename, xml_content)
        client = self._get_dian_client(company)

        for attempt in range(MAX_RETRIES):
            try:
                response = client.service.SendTestSetAsync(
                    fileName=filename.replace('.xml', '.zip'),
                    contentFile=content_file,
                    testSetId=test_set_id,
                )
                return self._parse_dian_response(response)

            except Exception as e:
                if attempt < MAX_RETRIES - 1 and self._is_transient_error(e):
                    delay = RETRY_DELAYS[attempt]
                    _logger.warning(
                        'DIAN SendTestSetAsync transient error (attempt %d/%d), retrying in %ds: %s',
                        attempt + 1, MAX_RETRIES, delay, str(e),
                    )
                    time.sleep(delay)
                    continue
                raise

    # =====================================================================
    # Response Parsing
    # =====================================================================

    def _parse_dian_response(self, response):
        """Parse a DIAN web service response into a standardized dict.

        :param response: zeep response object (SerialProxy)
        :return: dict with standardized fields
        """
        result = {
            'status_code': getattr(response, 'StatusCode', None),
            'status_description': getattr(response, 'StatusDescription', ''),
            'status_message': getattr(response, 'StatusMessage', ''),
            'is_valid': getattr(response, 'IsValid', False),
            'xml_document_key': getattr(response, 'XmlDocumentKey', ''),
            'zip_key': getattr(response, 'ZipKey', ''),
            'application_response': None,
            'errors': [],
            'raw_response': str(response),
        }

        # Parse ApplicationResponse XML if present
        xml_b64 = getattr(response, 'XmlBase64Bytes', None)
        if xml_b64:
            try:
                result['application_response'] = base64.b64decode(xml_b64).decode('utf-8')
            except Exception:
                result['application_response'] = xml_b64

        # Extract error messages
        error_messages = getattr(response, 'ErrorMessage', None)
        if error_messages:
            if isinstance(error_messages, (list, tuple)):
                result['errors'] = [str(e) for e in error_messages]
            elif hasattr(error_messages, 'string'):
                # zeep serializes string[] as object with 'string' attribute
                strings = getattr(error_messages, 'string', [])
                if isinstance(strings, (list, tuple)):
                    result['errors'] = [str(s) for s in strings]
                else:
                    result['errors'] = [str(strings)]
            else:
                result['errors'] = [str(error_messages)]

        return result

    def _is_dian_response_success(self, parsed_response):
        """Check if a parsed DIAN response indicates success.

        :param parsed_response: dict from _parse_dian_response
        :return: bool
        """
        status_code = parsed_response.get('status_code')
        is_valid = parsed_response.get('is_valid', False)
        status_desc = (parsed_response.get('status_description') or '').strip()

        # Success indicators
        if is_valid:
            return True
        if status_code in (DIAN_STATUS_OK, DIAN_STATUS_ACCEPTED):
            return True
        if status_desc == DIAN_STATUS_DOC_ACCEPTED:
            return True

        return False

    # =====================================================================
    # Error Handling
    # =====================================================================

    @staticmethod
    def _is_transient_error(exception):
        """Determine if an exception is a transient error worth retrying.

        :param exception: Exception instance
        :return: bool
        """
        import requests

        transient_types = (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ReadTimeout,
            ConnectionError,
            TimeoutError,
        )

        # Check for zeep transport errors
        try:
            from zeep.exceptions import TransportError
            transient_types = transient_types + (TransportError,)
        except ImportError:
            pass

        return isinstance(exception, transient_types)

    def _format_dian_error(self, parsed_response):
        """Format a DIAN error response into a user-readable message.

        :param parsed_response: dict from _parse_dian_response
        :return: str — formatted error message
        """
        parts = []
        if parsed_response.get('status_description'):
            parts.append(parsed_response['status_description'])
        if parsed_response.get('status_message'):
            parts.append(parsed_response['status_message'])
        if parsed_response.get('errors'):
            parts.extend(parsed_response['errors'])

        return ' | '.join(parts) if parts else _('Unknown DIAN error')
