import io
import zipfile
from datetime import datetime

import requests
from lxml import etree

from odoo import _
from odoo.tools.safe_eval import json

NS_STATUS = {"ns": "mfp:anaf:dgti:efactura:stareMesajFactura:v1"}
NS_HEADER = {"ns": "mfp:anaf:dgti:efactura:mesajEroriFactuta:v1"}
NS_DOWNLOAD = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
NS_SIGNATURE = {"ns": "http://www.w3.org/2000/09/xmldsig#"}


def make_efactura_request(session, company, endpoint, params, data=None) -> dict[str, str | bytes]:
    """
    Make an API request to the Romanian SPV, handle the response, and return a ``result`` dictionary.

    :param session: ``requests`` or ``requests.Session()`` object
    :param company: ``res.company`` object containing l10n_ro_edi_test_env, l10n_ro_edi_access_token
    :param endpoint: ``upload`` (for sending) | ``stareMesaj`` (for fetching status) | ``descarcare`` (for downloading answer) |``listaMesajeFactura`` (to obtain the latest messages from efactura)
    :param params: Dictionary of query parameters
    :param data: XML data for ``upload`` request
    :return: Dictionary of {'error': `str`, ['timeout': True for Timeout errors]} or {'content': <response.content>} from E-Factura
    """
    send_mode = 'test' if company.l10n_ro_edi_test_env else 'prod'
    url = f"https://api.anaf.ro/{send_mode}/FCTEL/rest/{endpoint}"
    if endpoint in ['upload', 'uploadb2c']:
        method = 'POST'
    elif endpoint in ['stareMesaj', 'descarcare', 'listaMesajeFactura']:
        method = 'GET'
    else:
        return {'error': _('Unknown endpoint.')}
    headers = {'Content-Type': 'application/xml',
               'Authorization': f'Bearer {company.l10n_ro_edi_access_token}'}

    try:
        response = session.request(method=method, url=url, params=params, data=data, headers=headers, timeout=60)
    except requests.HTTPError as e:
        return {'error': e}
    except (requests.ConnectionError, requests.Timeout):
        return {
            'error': _('Timeout while sending to SPV. Use Synchronise to SPV to update the status.'),
            'timeout': True,
        }

    if response.status_code == 204:
        return {'error': _('You reached the limit of requests. Please try again later.')}
    if response.status_code == 400:
        error_json = response.json()
        return {'error': error_json['message']}
    if response.status_code == 401:
        return {'error': _('Access token is unauthorized.')}
    if response.status_code == 403:
        return {'error': _('Access token is forbidden.')}
    if response.status_code == 500:
        return {'error': _('There is something wrong with the SPV. Please try again later.')}

    return {'content': response.content}


def _request_ciusro_send_invoice(company, xml_data, move_type='out_invoice', is_b2b=True):
    """
    This method makes an 'upload' request to send xml_data to Romanian SPV.Based on the result, it will then process
    the answer and return a dictionary, which may consist of either an 'error' or a 'key_loading' string.

    :param company: ``res.company`` object
    :param xml_data: String of XML data to be sent
    :param move_type: ``move_type`` field from ``account.move`` object, used for the request parameter
    :return: Result dictionary -> {'error': `str`} | {'key_loading': `str`}
    """
    result = make_efactura_request(
        session=requests,
        company=company,
        endpoint='upload' if is_b2b else 'uploadb2c',
        params={'standard': 'UBL' if move_type == 'out_invoice' else 'CN',
                'cif': company.vat.replace('RO', '')},
        data=xml_data,
    )
    if 'error' in result:
        # A timeout error in this case means that the invoice got received by SPV but did not get
        # its SPV index number, meaning that it will need to be re-synchronize later to obtain said index
        if 'timeout' in result:
            return {'key_loading': False}
        return result

    root = etree.fromstring(result['content'])
    res_status = root.get('ExecutionStatus')
    if res_status == '1':
        error_elements = root.findall('.//{mfp:anaf:dgti:efactura:stareMesajFactura:v1}Errors')
        error_messages = [error_element.get('errorMessage') for error_element in error_elements]
        return {'error': '\n'.join(error_messages)}
    return {'key_loading': root.get('index_incarcare')}


def _request_ciusro_fetch_status(company, key_loading, session):
    """
    This method makes a "Fetch Status" (GET/stareMesaj) request to the Romanian SPV. After processing the response,
    it will return one of the following three possible objects:

    - {'error': `str`} ~ failing response from a bad request
    - {'key_download': `str`, 'state_status': ['nok', 'ok']} ~ The response was successful, and we can use this key to download the answer.
    If the document was accepted, 'state_status' will be ``ok``. Otherwise, it will be ``nok``.
    - {} ~ (empty dict) The response was successful but the SPV haven't finished processing the XML yet.

    :param company: ``res.company`` object
    :param key_loading: Content of ``key_loading`` received from ``_request_ciusro_send_invoice``
    :param session: ``requests.Session()`` object
    :return: {'error': `str`} | {'key_download': `str`, 'state_status': ['nok', 'ok']} | {}
    """
    result = make_efactura_request(
        session=session,
        company=company,
        endpoint='stareMesaj',
        params={'id_incarcare': key_loading},
    )
    if 'error' in result:
        return result

    root = etree.fromstring(result['content'])
    error_elements = root.findall('.//ns:Errors', namespaces=NS_STATUS)
    if error_elements:
        return {'error': '\n'.join(error_element.get('errorMessage') for error_element in error_elements)}

    state_status = root.get('stare')
    if state_status in ('nok', 'ok'):
        return {'key_download': root.get('id_descarcare'), 'state_status': state_status}
    return {}


def _request_ciusro_download_answer(company, key_download, session):
    """
    This method makes a "Download Answer" (GET/descarcare) request to the Romanian SPV. It then processes the
    response by opening the received zip file and returns a dictionary containing:

    - the original invoice and/or the failing response from a bad request / unaccepted XML answer from the SPV
    - the necessary signature information to be stored from the SPV

    :param company: ``res.company`` object
    :param key_download: Content of `key_download` received from `_request_ciusro_send_invoice`
    :param session: ``requests.Session()`` object
    :return: - {'error': ``str``} if there has been an error during the request or parsing of the data
        - {
            'signature': {
                'attachment_raw': ``str``,
                'key_signature': ``str``,
                'key_certificate': ``str``,
            },
            'invoice': {
                'error': ``str``,
            } -> When the invoice is refused
            | {
                'name': ``str``,
                'amount_total': ``float``,
                'due_date': ``datetime``,
                'attachment_raw': ``str``,
            } -> When the invoice is accepted
        }
    """
    result = make_efactura_request(
        session=session,
        company=company,
        endpoint='descarcare',
        params={'id': key_download},
    )
    if 'error' in result:
        return result

    # E-Factura gives download response in ZIP format
    try:
        # The ZIP will contain two files,
        # one with the electronic signature (containing 'semnatura' in the filename),
        # and the other with one with the original invoice, the requested invoice or the identified errors.
        extracted_data = {'signature': {}, 'invoice': {}}
        with zipfile.ZipFile(io.BytesIO(result['content'])) as zip_ref:
            for file in zip_ref.infolist():
                file_bytes = zip_ref.read(file)
                root = etree.fromstring(file_bytes)

                # Extract the signature
                if 'semnatura' in file.filename:
                    attachment_raw = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
                    extracted_data['signature'] = {
                        'attachment_raw': attachment_raw,
                        'key_signature': root.findtext('.//ns:SignatureValue', namespaces=NS_SIGNATURE),
                        'key_certificate': root.findtext('.//ns:X509Certificate', namespaces=NS_SIGNATURE),
                    }

                # Extract the invoice or the errors if there are any
                else:
                    if error_elements := root.findall('.//ns:Error', namespaces=NS_HEADER):
                        extracted_data['invoice']['error'] = ('\n\n').join(error.get('errorMessage') for error in error_elements)

                    else:
                        extracted_data['invoice'] = {
                            'name': root.findtext('.//cbc:ID', namespaces=NS_DOWNLOAD),
                            'amount_total': root.findtext('.//cbc:TaxInclusiveAmount', namespaces=NS_DOWNLOAD),
                            'buyer_vat': root.findtext('.//cac:AccountingSupplierParty//cbc:CompanyID', namespaces=NS_DOWNLOAD),
                            'seller_vat': root.findtext('.//cac:AccountingCustomerParty//cbc:CompanyID', namespaces=NS_DOWNLOAD),
                            'date': datetime.strptime(root.findtext('.//cbc:IssueDate', namespaces=NS_DOWNLOAD), '%Y-%m-%d').date(),
                            'attachment_raw': file_bytes,
                        }
        return extracted_data

    except zipfile.BadZipFile:
        try:
            msg_content = json.loads(result['content'].decode())
        except ValueError:
            return {'error': _("The SPV data could not be parsed.")}

        if eroare := msg_content.get('eroare'):
            return {'error': eroare}

    return {'error': _("The SPV data could not be parsed.")}


def _request_ciusro_synchronize_invoices(company, session, nb_days=1):
    """
    This method makes a "Fetch Messages" (GET/listaMesajeFactura) request to the Romanian SPV.
    After processing the response, if messages were indeed fetched, it will fetch the content
    of said messages.

    Possible returns:
    - {'error': `str`} if there was a failing response from a bad request;
    - {'sent_invoices_messages': [`dict`], 'sent_invoices_refused_messages': [`dict`], 'received_bills_messages': [`dict`]}
    where `dict` is {
        'data_creare': `str`,
        'cif': `str`,
        'id_solicitare': `str`,
        'detalii': `str`,
        'tip': 'FACTURA TRIMISA'|'ERORI FACTURA'|'FACTURA PRIMITA',
        'id': `str`,
        'answer': <`_request_ciusro_download_answer`>
    } representing a message.
    sent_invoices_messages will contain all message validating an invoice, sent_invoices_refused_messages will contain all messages refusing an invoice
    and received_bills_messages will contain all message representing received bills.

    :param company: ``res.company`` object
    :param session: ``requests.Session()`` object
    :param nb_days(optional,default=1): ``int`` the number of days for which the request should be made, min=1, max=60
    :return: {'error': `str`} | {'sent_invoices_messages': [`dict`], 'sent_invoices_refused_messages': [`dict`], 'received_bills_messages': [`dict`]}
    """
    result = make_efactura_request(
        session=session,
        company=company,
        endpoint='listaMesajeFactura',
        params={'zile': nb_days, 'cif': company.vat.replace('RO', '')},
    )
    if 'error' in result:
        return {'error': result['error']}

    try:
        msg_content = json.loads(result['content'])
    except ValueError:
        return {'error': _("The SPV data could not be parsed.")}

    if eroare := msg_content.get('eroare'):
        return {'error': eroare}

    received_bills_messages = []
    sent_invoices_accepted_messages = []
    sent_invoices_refused_messages = []
    for message in msg_content.get('mesaje'):
        message['answer'] = _request_ciusro_download_answer(
            key_download=message['id'],
            company=company,
            session=session,
        )
        if message['tip'] == 'FACTURA TRIMISA':
            sent_invoices_accepted_messages.append(message)
        elif message['tip'] == 'ERORI FACTURA':
            sent_invoices_refused_messages.append(message)
        elif message['tip'] == 'FACTURA PRIMITA':
            received_bills_messages.append(message)

    return {
        'sent_invoices_accepted_messages': sent_invoices_accepted_messages,
        'sent_invoices_refused_messages': sent_invoices_refused_messages,
        'received_bills_messages': received_bills_messages
    }
