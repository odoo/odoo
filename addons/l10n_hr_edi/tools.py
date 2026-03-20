"""
MojEracun version of the proxy user model, set up as an AbstractModel as the data is held on res_company.
The integration requires a lot of adjustments to work directly with an extrenal service provier and the original
edi_proxy_user cannot be used as a basis as it is too closely tied to Odoo's own IAP server structure.
"""

import logging
import requests
from json import JSONDecodeError

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
TIMEOUT = 30


class MojEracunServiceError(Exception):

    def __init__(self, code, message=False):
        self.code = code
        self.message = message
        super().__init__(message or code)


# -------------------------------------------------------------------------
# HELPER METHODS
# -------------------------------------------------------------------------

def _get_server_url(company, edi_mode=None):
    edi_mode = edi_mode or company.l10n_hr_mer_connection_mode
    urls = {
        'prod': 'https://www.moj-eracun.hr',
        'test': 'https://demo.moj-eracun.hr',
        'demo': '???',
    }
    return urls[edi_mode]


def _make_request(company, endpoint_type, params=False):
    """
    Returns:
        For multiple document endpoints (such as query*): list of dicts
        For single document endpoints (such as markPaid): dict
        For receive specifically: bytestring
    """
    endpoints = {
        'send': '/apis/v2/send',
        'query_inbox': '/apis/v2/queryInbox',
        'receive': '/apis/v2/receive',
        'update_status': '/apis/v2/UpdateDokumentProcessStatus',
        'query_status_inbox': '/apis/v2/queryDocumentProcessStatusInbox',
        'query_status_outbox': '/apis/v2/queryDocumentProcessStatusOutbox',
        'notify_import': False,  # Includes eID and has to be handled separately
        'mark_paid': '/api/fiscalization/markPaid',
        'reject': '/api/fiscalization/reject',
        'fisc_outbox': '/api/fiscalization/statusOutbox',
        'fisc_inbox': '/api/fiscalization/statusInbox',
    }
    endpoint = f"/apis/v2/notifyimport/{params.pop('eid')}" if endpoint_type == 'notify_import' else endpoints.get(endpoint_type)
    if not endpoint:
        raise MojEracunServiceError('Invalid API endpoint')
    payload = params
    url = f"{_get_server_url(company)}{endpoint}"

    # Last barrier : in case the demo mode is not handled by the caller, we block access.
    if company.l10n_hr_mer_connection_mode == 'demo':
        raise MojEracunServiceError("block_demo_mode", "Can't access the proxy in demo mode")

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=TIMEOUT,
            headers={'content-type': 'application/json', 'charset': 'utf-8'}
        )
    except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError):
        raise MojEracunServiceError('connection_error',
            company.env._('The url that this service requested returned an error. The url it tried to contact was %s', url))

    # Structure-specific error handling
    if response.status_code != 200:
        try:
            error_message = response.json()
            error_message = error_message.get('errors') or error_message.get('message')
        except (JSONDecodeError, TypeError):
            error_message = False
        raise UserError(company.env._("Error handling request: %s", error_message) if error_message else company.env._("HTTP %s: Connection error.", response.status_code))

    if endpoint != endpoints['receive']:
        try:
            response_json = response.json()
        except (JSONDecodeError, TypeError):
            raise MojEracunServiceError('Invalid response format received')
        if 'error' in response_json:
            message = company.env._('The url that this service requested returned an error. The url it tried to contact was %(url)s. %(error_message)s', url=url, error_message=response_json['error']['message'])
            if response_json['error']['code'] == 404:
                message = company.env._('The url that this service tried to contact does not exist. The url was “%s”', url)
            raise MojEracunServiceError('connection_error', message)
        return response_json
    else:
        return response.content


def _call_mer_service(company, endpoint, params=None):
    params_base = {
        'Username': company.l10n_hr_mer_username,
        'Password': company.l10n_hr_mer_password,
        'CompanyId': company.l10n_hr_mer_company_ident,
        'CompanyBu': company.partner_id.l10n_hr_business_unit_code,
        'SoftwareId': company.l10n_hr_mer_software_ident,
    }
    if params:
        params = params_base | params
    else:
        params = params_base
    params_to_delete = []
    for key, value in params.items():
        if not value:
            params_to_delete.append(key)
    for key in params_to_delete:
        params.pop(key)
    try:
        response = _make_request(
            company,
            endpoint,
            params=params,
        )
    except MojEracunServiceError as e:
        raise UserError(e)

    return response


# -------------------------------------------------------------------------
# MOJERACUN API CALL METHODS
# -------------------------------------------------------------------------

def _mer_api_send(company, xml_file):
    """
    Send electronic document to a recipient.
    """
    params = {
        'File': xml_file,
    }
    response_dict = _call_mer_service(company, 'send', params=params)
    return response_dict


def _mer_api_query_inbox(company, filter=None, electronic_id=None, status_id=None, date_from=None, date_to=None):
    """
    Status description. Query methods are refered as basic MER document statuses.
    When receiving response from query methods, you will get croatian names of statuses
    (U obradi, Poslan, Preuzet, Povučeno preuzimanje, Neuspjelo).
    """
    params = {
        'Filter': filter,
        'ElectronicId': electronic_id,
        'StatusId': status_id,
        'From': date_from,
        'To': date_to,
    }
    response_list = _call_mer_service(company, 'query_inbox', params=params)
    return response_list


def _mer_api_receive_document(company, electronic_id):
    """
    Receive method is used for downloading documents. Both sent and incoming, eg. Inbox and Outbox documents.
    """
    params = {
        'ElectronicId': electronic_id,
    }
    response_bstr = _call_mer_service(company, 'receive', params=params)
    if response_bstr[:5] != b'<?xml':
        raise MojEracunServiceError('service_error', company.env._("Failed to retrieve document XML for ElectronicId: %s", electronic_id))
    return response_bstr


def _mer_api_update_document_process_status(company, electronic_id, status_id, rejection_reason=None):
    """
    Document process status codes are used to update status of document after it has been
    downloaded or received in the system of the another information provider / access points.
    They are also referred as business document statuses.
    Statuses 4 and 99 cannot be modified via API.
    """
    params = {
        'ElectronicId': electronic_id,
        'StatusId': status_id,
        'RejectReason': rejection_reason,
    }
    response_dict = _call_mer_service(company, 'update_status', params=params)
    return response_dict


def _mer_api_query_document_process_status_inbox(company, electronic_id=None, status_id=None, invoice_year=None, invoice_number=None, date_from=None, date_to=None, by_update_date=None):
    """
    Query inbox is used to discover new documents sent to your company or business unit. For this method, the API returns 20.000 results.
    """
    params = {
        'ElectronicId': electronic_id,
        'StatusId': status_id,
        'InvoiceYear': invoice_year,
        'InvoiceNumber': invoice_number,
        'DateFrom': date_from,
        'DateTo': date_to,
        'ByUpdateDate': by_update_date,
    }
    response_list = _call_mer_service(company, 'query_status_inbox', params=params)
    return response_list


def _mer_api_query_document_process_status_outbox(company, electronic_id=None, status_id=None, invoice_year=None, invoice_number=None, date_from=None, date_to=None, by_update_date=None):
    """
    Query inbox is used to discover new documents sent to your company or business unit. For this method, the API returns 20.000 results.
    """
    params = {
        'ElectronicId': electronic_id,
        'StatusId': status_id,
        'InvoiceYear': invoice_year,
        'InvoiceNumber': invoice_number,
        'DateFrom': date_from,
        'DateTo': date_to,
        'ByUpdateDate': by_update_date,
    }
    response_list = _call_mer_service(company, 'query_status_outbox', params=params)
    return response_list


def _mer_api_notify_import(company, electronic_id):
    """
    Notify import method is used for sending an information that an invoice is imported into an ERP.
    You can use it to update which document you have successfully imported and to make procedure for
    importing  only documents that you previously did not download and import.
    """
    response_dict = _call_mer_service(company, 'notify_import', params={'eid': electronic_id})
    return response_dict


def _mer_api_mark_paid(company, electronic_id, payment_date, payment_amount, payment_method):
    """
    Methods for sending payment information for sent documents.
    """
    params = {
        'ElectronicId': electronic_id,
        'PaymentDate': payment_date,
        'PaymentAmount': payment_amount,
        'PaymentMethod': payment_method,
    }
    response_dict = _call_mer_service(company, 'mark_paid', params=params)
    return response_dict


def _mer_api_reject_with_id(company, electronic_id, rejection_date, rejection_type, rejection_desc):
    """
    Methods for sending information regarding rejection for received electronic documents.
    """
    params = {
        'ElectronicId': electronic_id,
        'RejectionDate': rejection_date,
        'RejectionReasonType': rejection_type,
        'RejectionReasonDescription': rejection_desc,
    }
    response_dict = _call_mer_service(company, 'reject', params=params)
    return response_dict


def _mer_api_check_fiscalization_status_outbox(company, electronic_id=False, message_type=False, date_from=False, date_to=False, by_update_date=False, request_id=False, status=False):
    """
    This endpoint retrieves the fiscalization status of a document using its ElectronicId and MessageType.
    """
    params = {
        'ElectronicId': electronic_id,
        'MessageType': message_type,
        'DateFrom': date_from,
        'DateTo': date_to,
        'ByUpdateDate': by_update_date,
        'FiscalizationRequestID': request_id,
        'Status': status,
    }
    response_list = _call_mer_service(company, 'fisc_outbox', params=params)
    return response_list


def _mer_api_check_fiscalization_status_inbox(company, electronic_id=False, message_type=False, date_from=False, date_to=False, by_update_date=False, request_id=False, status=False):
    """
    This endpoint retrieves the fiscalization status of a document using its ElectronicId and MessageType.
    """
    params = {
        'ElectronicId': electronic_id,
        'MessageType': message_type,
        'DateFrom': date_from,
        'DateTo': date_to,
        'ByUpdateDate': by_update_date,
        'FiscalizationRequestID': request_id,
        'Status': status,
    }
    response_list = _call_mer_service(company, 'fisc_inbox', params=params)
    return response_list
