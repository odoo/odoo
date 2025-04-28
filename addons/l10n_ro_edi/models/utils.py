import io
import zipfile
from datetime import datetime

import requests
from lxml import etree

from odoo import _
from odoo.tools.safe_eval import json

NS_UPLOAD = {"ns": "mfp:anaf:dgti:spv:respUploadFisier:v1"}
NS_STATUS = {"ns": "mfp:anaf:dgti:efactura:stareMesajFactura:v1"}
NS_HEADER = {"ns": "mfp:anaf:dgti:efactura:mesajEroriFactuta:v1"}
NS_DOWNLOAD = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"}
NS_SIGNATURE = {"ns": "http://www.w3.org/2000/09/xmldsig#"}


def make_efactura_request(session, company, endpoint, method, params, data=None) -> dict[str, str | bytes]:
    """
    Make an API request to the Romanian SPV, handle the response, and return a ``result`` dictionary.

    :param session: ``requests`` or ``requests.Session()`` object
    :param company: ``res.company`` object containing l10n_ro_edi_test_env, l10n_ro_edi_access_token
    :param endpoint: ``upload`` (for sending) | ``stareMesaj`` (for fetching status) | ``descarcare`` (for downloading answer) |``listaMesajeFactura`` (to obtain the latest messages from efactura)
    :param method: ``post`` (for `upload`) | ``get`` (for `stareMesaj` | `descarcare`)
    :param params: Dictionary of query parameters
    :param data: XML data for ``upload`` request
    :return: Dictionary of {'error': <str>} or {'content': <response.content>} from E-Factura
    """
    send_mode = 'test' if company.l10n_ro_edi_test_env else 'prod'
    url = f"https://api.anaf.ro/{send_mode}/FCTEL/rest/{endpoint}"
    headers = {'Content-Type': 'application/xml',
               'Authorization': f'Bearer {company.l10n_ro_edi_access_token}'}

    try:
        response = session.request(method=method, url=url, params=params, data=data, headers=headers, timeout=30)  # ABOO: Put back 60
        response.raise_for_status()
    except requests.HTTPError as e:
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
        return {'error': e}
    except (requests.ConnectionError, requests.Timeout):
        return {'error': _('The SPV server is currently unavailable, please try again later.')}

    return {'content': response.content}


def _request_ciusro_send_invoice(company, xml_data, move_type='out_invoice', is_b2b=True):
    """
    This method makes an 'upload' request to send xml_data to Romanian SPV.Based on the result, it will then process
    the answer and return a dictionary, which may consist of either an 'error' or a 'key_loading' string.

    :param company: ``res.company`` object
    :param xml_data: String of XML data to be sent
    :param move_type: ``move_type`` field from ``account.move`` object, used for the request parameter
    :return: Result dictionary -> {'error': <str>} | {'key_loading': <str>}
    """
    result = make_efactura_request(
        session=requests,
        company=company,
        endpoint='upload' if is_b2b else 'uploadb2c',
        method='POST',
        params={'standard': 'UBL' if move_type == 'out_invoice' else 'CN',
                'cif': company.vat.replace('RO', '')},
        data=xml_data,
    )
    if 'error' in result:
        return result

    root = etree.fromstring(result['content'])
    res_status = root.get('ExecutionStatus')
    if res_status == '1':
        error_elements = root.findall('.//ns:Errors', namespaces=NS_UPLOAD)
        error_messages = [error_element.get('errorMessage') for error_element in error_elements]
        return {'error': '\n'.join(error_messages)}
    return {'key_loading': root.get('index_incarcare')}


def _request_ciusro_fetch_status(company, key_loading, session):
    """
    This method makes a "Fetch Status" (GET/stareMesaj) request to the Romanian SPV. After processing the response,
    it will return one of the following three possible objects:

    - {'error': <str>} ~ failing response from a bad request
    - {'key_download': <str>, 'state_status': ['nok', 'ok']} ~ The response was successful, and we can use this key to download the answer. 
    If the document was accepted, 'state_status' will be ``ok``. Otherwise, it will be ``nok``.
    - {} ~ (empty dict) The response was successful but the SPV haven't finished processing the XML yet.

    :param company: ``res.company`` object
    :param key_loading: Content of ``key_loading`` received from ``_request_ciusro_send_invoice``
    :param session: ``requests.Session()`` object
    :return: {'error': <str>} | {'key_download': <str>, 'state_status': ['nok', 'ok']} | {}
    """
    result = make_efactura_request(
        session=session,
        company=company,
        endpoint='stareMesaj',
        method='GET',
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
    :return: {'error': ``str``, 'signature': {'attachment_raw': ``str``, 'key_signature': ``str``, 'key_certificate': ``str``}, 'invoice': {'name': ``str``, 'amount_total': ``float``, 'due_date': ``datetime``, 'invoice_raw': ``str``}}
    """
    result = make_efactura_request(
        session=session,
        company=company,
        endpoint='descarcare',
        method='GET',
        params={'id': key_download},
    )
    extracted_data = {'error': "", 'signature': {}, 'invoice': {}}

    if 'error' in result:
        extracted_data['error'] = result['error']
        return extracted_data

    # E-Factura gives download response in ZIP format
    try:
        zip_ref = zipfile.ZipFile(io.BytesIO(result['content']))
    except zipfile.BadZipFile:
        try:
            msg_content = json.loads(result['content'].decode())
        except ValueError:
            extracted_data['error'] = _("The SPV data could not be parsed.")
            return extracted_data

        if eroare := msg_content.get('eroare'):
            extracted_data['error'] = eroare
            return extracted_data

    # The ZIP will contain two files,
    # one with the electronic signature (containing 'semnatura' in the filename),
    # and the other with one with the original invoice, the requested invoice or the identified errors.
    for file_name in zip_ref.namelist():
        file_bytes = zip_ref.read(file_name)
        root = etree.fromstring(file_bytes)

        # Extract the signature
        if 'semnatura' in file_name:
            attachment_raw = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
            extracted_data['signature'] = {
                'attachment_raw': attachment_raw,
                'key_signature': root.findtext('.//ns:SignatureValue', namespaces=NS_SIGNATURE),
                'key_certificate': root.findtext('.//ns:X509Certificate', namespaces=NS_SIGNATURE),
            }

        # Extract the invoice and the errors if there are any
        else:
            error_elements = root.findall('.//ns:Error', namespaces=NS_HEADER)
            if error_elements:
                extracted_data['error'] = ('\n\n').join(error.get('errorMessage') for error in error_elements)

            else:
                # ABOO: Shouldn't we extract more data to search on later ?
                extracted_data['invoice'] = {
                    'name': root.findtext('.//cbc:ID', namespaces=NS_DOWNLOAD),
                    'amount_total': root.findtext('.//cbc:TaxInclusiveAmount', namespaces=NS_DOWNLOAD),
                    'due_date': datetime.strptime(root.findtext('.//cbc:DueDate', namespaces=NS_DOWNLOAD), '%Y-%m-%d').date(),
                    'invoice_raw': file_bytes,
                }

    zip_ref.close()
    return extracted_data


def _request_ciusro_synchronize_invoices(company, session, nb_days=1):
    """
    This method makes a "Fetch Messages" (GET/listaMesajeFactura) request to the Romanian SPV.
    After processing the response, if messages were indeed fetched, it will fetch the content
    of said messages.

    Possible returns:

    - {'error': <str>} if there was a failing response from a bad request;
    - {'messages': [<dict>]} where <dict> is {TODO ABOO}; the list a message and content of the messages;

    :param company: ``res.company`` object
    :param session: ``requests.Session()`` object
    :param nb_days(optional,default=1): ``int`` the number of days for which the request should be made, min=1, max=60
    :return: {'error': <str>} | {'messages': [<dict>]}
    """
    result = make_efactura_request(
        session=session,
        company=company,
        endpoint='listaMesajeFactura',
        method='GET',
        params={'zile': 60, 'cif': company.vat.replace('RO', '')},  # TODO ABOO: change back zile to 1
    )
    if 'error' in result:
        return {'error': result['error']}

    try:
        msg_content = json.loads(result['content'].decode())
    except ValueError:
        return {'error': _("The SPV data could not be parsed.")}

    if eroare := msg_content.get('eroare'):
        return {'error': eroare}

    messages = msg_content.get('mesaje')
    for msg in messages:
        # ABOO: Use `id_solicitare` to find the invoice object and the `id` to request a status update

        if msg['tip'] in ['FACTURA PRIMITA', 'FACTURA TRIMISA', 'ERORI FACTURA']:
            msg['answer'] = _request_ciusro_download_answer(
                    key_download=msg['id'],
                    company=company,
                    session=session,
                )

        elif msg.get('tip') in ['MESAJ CUMPARATOR PRIMIT', 'MESAJ CUMPARATOR TRANSMIS']:
            pass

    return {'messages': messages}
