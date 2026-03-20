import io
import zipfile
from datetime import datetime, timedelta

import requests
from lxml import etree

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
    :param endpoint: ``upload`` (for sending) | ``stareMesaj`` (for fetching status) | ``descarcare`` (for downloading answer) |``listaMesajeFactura`` (to obtain the latest messages from efactura) | ``transformare`` (to get the official PDF from efactura)
    :param params: Dictionary of query parameters
    :param data: XML data for ``upload`` request
    :return: Dictionary of {'error': `str`, ['timeout': True for Timeout errors]} or {'content': <response.content>} from E-Factura
    """
    send_mode = 'test' if company.l10n_ro_edi_test_env else 'prod'
    url = f"https://api.anaf.ro/{send_mode}/FCTEL/rest/{endpoint}"
    if endpoint in ['upload', 'uploadb2c', 'transformare']:
        method = 'POST'
    elif endpoint in ['stareMesaj', 'descarcare', 'listaMesajeFactura', 'listaMesajePaginatieFactura']:
        method = 'GET'
    else:
        return {'error': company.env._('Unknown endpoint.')}
    headers = {'Content-Type': 'application/xml',
               'Authorization': f'Bearer {company.l10n_ro_edi_access_token}'}
    if endpoint == 'transformare':
        url = "https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/%s/%s" % (
            params.get("standard", "FACT1"), params.get("novld", "DA")
        )
        headers = {'Content-Type': 'text/plain'}

    try:
        response = session.request(method=method, url=url, params=params, data=data, headers=headers, timeout=60)
    except requests.HTTPError as e:
        return {'error': e}
    except (requests.ConnectionError, requests.Timeout):
        return {
            'error': company.env._('Timeout while sending to SPV. Use Synchronise to SPV to update the status.'),
            'timeout': True,
        }

    if response.status_code == 204:
        return {'error': company.env._('You reached the limit of requests. Please try again later.')}
    if response.status_code == 400:
        error_json = response.json()
        return {'error': error_json['message']}
    if response.status_code == 401:
        return {'error': company.env._('Access token is unauthorized.')}
    if response.status_code == 403:
        return {'error': company.env._('Access token is forbidden.')}
    if response.status_code == 500:
        return {'error': company.env._('There is something wrong with the SPV. Please try again later.')}

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
    - {'key_download': `str`, 'state_status': ['nok', 'ok', 'XML cu erori nepreluat de sistem']} ~ The response was successful, and we can use this key to download the answer.
    If the document was accepted, 'state_status' will be ``ok``. Otherwise, it will be ``nok`` or special case ``XML cu erori nepreluat de sistem`` if the XML was not accepted by SPV due to errors but it was not rejected either, meaning that the supplier will need to correct the XML and resend it.
    - {} ~ (empty dict) The response was successful but the SPV haven't finished processing the XML yet.

    :param company: ``res.company`` object
    :param key_loading: Content of ``key_loading`` received from ``_request_ciusro_send_invoice``
    :param session: ``requests.Session()`` object
    :return: {'error': `str`} | {'key_download': `str`, 'state_status': ['nok', 'ok', 'XML cu erori nepreluat de sistem']} | {}
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
    if state_status != 'in prelucrare':
        return {'key_download': root.get('id_descarcare'), 'state_status': state_status}
    return {}


def _request_ciusro_download_answer(company, key_download, session):
    """
    This method makes a "Download Answer" (GET/descarcare) request to the Romanian SPV. It then processes the
    response by opening the received zip file and returns a dictionary containing:

    - the original invoice and/or the failing response from a bad request / unaccepted XML answer from the SPV
    - the necessary signature information to be stored from the SPV

    It could return also a JSON with an error message if the SPV response cannot be parsed or if the SPV returned an error.
    {
        "eroare": "Id descarcare introdus= 123a nu este un numar intreg",
        "titlu": "Descarcare mesaj"
    }
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
            msg_content = json.loads(result.get('content', b''))
        except ValueError:
            return {'error': company.env._("The SPV data could not be parsed.")}

        if error := msg_content.get('eroare'):
            return {'error': error}

    return {'error': company.env._("The SPV data could not be parsed.")}


def _request_ciusro_synchronize_invoices_pagination(company, session, nb_days=1):
    """
    This method makes a "Fetch Messages" (GET/listaMesajePaginatieFactura) request to the Romanian SPV.
    and process the response, getting the list of messages and errors. It used the pagination system of
    the SPV to make sure all messages are fetched, by default only the first 500 are shown, so in case
    of bigger comapnies, this method needs to be paginated.

    Returns:
    Returns a dict with messages and errors keys, messages is a list of all messages obtained from SPV and
    errors is a list of all errors encountered during the pagination request or the fetching of the message content.
    - {messages: [`dict`], errors: [`str`]}
    where `dict` is {
        'data_creare': `str`,
        'cif': `str`,
        'id_solicitare': `str`,
        'detalii': `str`,
        'tip': 'FACTURA TRIMISA'|'ERORI FACTURA'|'FACTURA PRIMITA',
        'id': `str`,
        'answer': <`_request_ciusro_download_answer`>
    } representing a message.

    :param company: ``res.company`` object
    :param session: ``requests.Session()`` object
    :param nb_days(optional,default=1): ``int`` the number of days for which the request should be made, min=1, max=60
    """
    messages = []
    errors = []
    nb_days = max(1, min(nb_days, 60))  # Ensure nb_days is between 1 and 60 as per SPV limits
    start_time = str((datetime.now() - timedelta(days=nb_days)).timestamp() * 1e3).split(".")[0]
    end_time = str(datetime.now().timestamp() * 1e3).split(".")[0]
    page_number = 1
    result = make_efactura_request(
        session=session,
        company=company,
        endpoint='listaMesajePaginatieFactura',
        params={'startTime': start_time, 'endTime': end_time, 'cif': company.vat.replace('RO', ''), 'pagina': page_number},
    )

    total_page_number = result.get('numar_total_pagini', 1)
    while page_number <= total_page_number:
        if page_number > 1:
            result = make_efactura_request(
                session=session,
                company=company,
                endpoint='listaMesajePaginatieFactura',
                params={'startTime': start_time, 'endTime': end_time, 'cif': company.vat.replace('RO', ''), 'pagina': page_number},
            )
        if 'content' in result:
            result = json.loads(result['content'])

        messages += result.get('mesaje', [])
        if result.get("error"):
            errors.append(result.get("error"))
        if result.get("eroare"):
            errors.append(result.get("eroare"))

        page_number += 1

    return {'messages': messages, 'errors': errors}


def _request_ciusro_synchronize_invoices(company, session, nb_days=1):
    """ This method processes the messages obtained from _request_ciusro_synchronize_invoices_pagination
    by fetching the content of each message and separating them into three categories:
    - Accepted sent invoices messages (representing the accepted status of an invoice sent to SPV)
    - Refused sent invoices messages (representing the refused status of an invoice sent to SPV)
    - Received bills messages (representing the received status of an invoice received from SPV)
    - Errors during the pagination request or the fetching of the message content
    - {'sent_invoices_messages': [`dict`], 'sent_invoices_refused_messages': [`dict`], 'received_bills_messages': [`dict`], 'errors': [`str`]}
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
    """
    message_response = _request_ciusro_synchronize_invoices_pagination(company, session, nb_days=nb_days)
    messages = message_response.get('messages', [])
    errors = message_response.get('errors', [])
    received_bills_messages = []
    sent_invoices_accepted_messages = []
    sent_invoices_refused_messages = []
    for message in messages:
        # This method takes a lot of time, if you have a lot of messages
        # so would be good to recheck it or if it's really needed for all
        # messages, for purchase invoice, I don't see it required,
        # but it is used also in _l10n_ro_edi_process_bill_messages.
        # Probably we can check before for which the response is needed.
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
        'received_bills_messages': received_bills_messages,
        'errors': errors
    }


def _request_ciusro_xml_to_pdf(company, xml_data):
    """
    This method makes a 'transformare' request to get the official PDF of an invoice.
    The response can be the PDF file if the transformation is successful, or a json
    with some error messages if the transformation failed.
    {
    "stare": "nok",
    "Messages": [
        {
        "message": "Valorile acceptate pentru parametrul standard sunt FACT1 si FCN"
        }
    ],
    "trace_id": "4506b709-92d1-4efe-b286-e652624ba2fb"
    }
    :param company: ``res.company`` object
    :param xml_data: String of XML data to be sent
    :return: response dict from E-Factura
    """
    # TO-DO: Migrate in next release to parameters instead of context for
    # better clarity and maintainability
    inv_type = company.env.context.get("render_anaf_pdf_type", "FACT1")
    result = make_efactura_request(
        session=requests,
        company=company,
        endpoint='transformare',
        params={'standard': inv_type,
                'novld': 'DA'},
        data=xml_data,
    )
    # If result is of type json, we need to handle the error messages received from SPV, otherwise we return the PDF content
    if 'stare' in result:
        # Get the error messages from the response and return them in a string separated by \n
        error_messages = [message.get('message') for message in result.get('Messages', [])]
        return {'error': '\n'.join(error_messages)}
    return result
