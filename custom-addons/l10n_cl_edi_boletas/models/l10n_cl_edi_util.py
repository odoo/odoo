# -*- coding: utf-8 -*-
import collections
import logging
import requests
import urllib3
from lxml import etree

from werkzeug.urls import url_join

from odoo import _, models

_logger = logging.getLogger(__name__)

# REFACTOR: This could be move to the parent model
MSG_ERROR = {
    'token': _('Token cannot be generated. Please try again'),
    'send': _('Sending DTE to SII failed due to:') + '<br /> %s',
    'status': _('Ask for DTE status to SII failed due to:') + '<br /> %s',
}

REST_SERVER_URL = {
        'SIITEST': {
            'SEND': 'https://pangal.sii.cl/recursos/v1/boleta.electronica.envio',
            'OTHER': 'https://apicert.sii.cl/recursos/v1/'
        },
        'SII': {
            'SEND': 'https://rahue.sii.cl/recursos/v1/boleta.electronica.envio',
            'OTHER': 'https://api.sii.cl/recursos/v1/'
        },
        'SIIDEMO': {
            'SEND': 'https://pangal.sii.cl/recursos/v1/boleta.electronica.envio',
            'OTHER': 'https://apicert.sii.cl/recursos/v1/'
        },
}

SII_DETAIL_STATUS_RESULTS_REST = {
    **dict.fromkeys(['DOK'], 'accepted'),
    **dict.fromkeys(['RPR', 'RLV'], 'objected'),
    **dict.fromkeys(['RCH'], 'rejected'),
}

TIMEOUT_REST = 5


class L10nClEdiUtilMixin(models.AbstractModel):
    _inherit = 'l10n_cl.edi.util'

    def _get_seed_rest(self, mode):
        url = url_join(REST_SERVER_URL[mode]['OTHER'], 'boleta.electronica.semilla')
        response = requests.get(url, timeout=TIMEOUT_REST)
        if not response.ok:
            return None
        return etree.fromstring(response.content).findtext('*/SEMILLA')

    def _get_token_rest(self, mode, digital_signature):
        if mode == 'SIIDEMO':
            return digital_signature.last_token
        if digital_signature.last_rest_token:
            return digital_signature.last_rest_token
        seed = self._get_seed_rest(mode)
        if not seed:
            return self._connection_exception('exception', _('Not possible to get a seed'))

        headers = {'Accept': 'application/xml', 'Content-Type': 'application/xml'}
        url = url_join(REST_SERVER_URL[mode]['OTHER'], 'boleta.electronica.token')
        signed_token = self._get_signed_token(digital_signature, seed)
        response = requests.post(url, headers=headers, data=signed_token, timeout=TIMEOUT_REST)
        if not response.ok:
            return None
        token = etree.fromstring(response.content).findtext('*/TOKEN')
        digital_signature.last_rest_token = token
        return token

    def _send_xml_to_sii_rest(self, mode, company_vat, file_name, xml_message, digital_signature):
        token = self._get_token_rest(mode, digital_signature)
        if token is None:
            self._report_connection_err(MSG_ERROR['token'])
            return False

        # The attributes must be ordered and the file (archivo key) must be added as data content, otherwise doesn't
        # work
        data = collections.OrderedDict()
        data['rutSender'] = int(digital_signature['subject_serial_number'][:-2])
        data['dvSender'] = digital_signature['subject_serial_number'][-1]
        data['rutCompany'] = self._l10n_cl_format_vat(company_vat)[:-2]
        data['dvCompany'] = self._l10n_cl_format_vat(company_vat)[-1]
        data['archivo'] = (file_name, xml_message, 'text/xml')

        (content, content_type) = urllib3.filepost.encode_multipart_formdata(data)
        # The User-Agent parameter is mandatory. The service is very picky with it so it set as the
        # same User-Agent used in the documentation, using other User-Agent like 'python-requests/2.21.0' or
        # 'Odoo (http://www.odoo.com/contactus)' or 'Mozilla/4.0 ( compatible; Odoo %s )' % release.series
        # causes a "Token not valid" response
        # ref: https://www4c.sii.cl/bolcoreinternetui/api/
        headers = {
            'accept': 'application/json',
            'Cookie': 'TOKEN={}'.format(token),
            'User-Agent': 'Mozilla/4.0 ( compatible; PROG 1.0; Windows NT)',
            'Content-Type': content_type
        }
        if mode == 'SIIDEMO':
            return None
        try:
            response = requests.post(REST_SERVER_URL[mode]['SEND'], headers=headers, data=content, timeout=TIMEOUT_REST)
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as error:
            self._report_connection_err(MSG_ERROR['send'] % error)
            return None

        if response.status_code == 401:
            _logger.info('Token is not valid. Retrying send DTE to SII')
            digital_signature.last_rest_token = False
            return self._send_xml_to_sii_rest(mode, company_vat, file_name, xml_message, digital_signature)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            self._report_connection_err(MSG_ERROR['send'] % error)
            return None
        return response.json()

    def _get_send_status_rest(self, mode, track_id, company_vat, digital_signature):
        token = self._get_token_rest(mode, digital_signature)
        if token is None:
            self._report_connection_err(MSG_ERROR['token'])
            return False
        url = url_join(REST_SERVER_URL[mode]['OTHER'],
                       'boleta.electronica.envio/%s-%s-%s' % (company_vat[:-2], company_vat[-1], track_id))
        if mode == 'SIIDEMO':
            return None
        try:
            response = requests.get(url, headers={'Cookie': 'TOKEN={}'.format(token)}, timeout=TIMEOUT_REST)
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as error:
            self._report_connection_err(MSG_ERROR['status'] % error)
            return None

        if response.status_code == 401:
            _logger.info('Token is not valid. Retrying verify DTE status')
            digital_signature.last_rest_token = False
            return self._get_send_status_rest(mode, track_id, company_vat, digital_signature)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            self._report_connection_err(MSG_ERROR['status'] % error)
            return None
        return response.json()

    def _analyze_sii_result_rest(self, message):
        detail_rep_rech = message.get('detalle_rep_rech', [])
        if detail_rep_rech is None:
            return 'ask_for_status'
        for doc in detail_rep_rech:
            detail_status = SII_DETAIL_STATUS_RESULTS_REST.get(doc['estado'])
            if doc['folio'] is None and detail_status == 'rejected':
                return 'rejected'
            matching_folio = doc.get('folio') == int(self.l10n_latam_document_number)
            matching_tipo = doc.get('tipo') == int(self.l10n_latam_document_type_id.code)
            if detail_status is not None and matching_folio and matching_tipo:
                return detail_status
        # The message may or may not include data into the 'detalle_rep_rech' section so the number of the DTE
        # reported, objected and accepted will be verified from the 'estadistica' section. For now the message will
        # only include a DTE.
        for summary in message.get('estadistica', []):
            if summary['tipo'] != int(self.l10n_latam_document_type_id.code):
                continue
            if summary['aceptados'] == summary['informados']:
                return 'accepted'
            if summary['reparos'] >= 1:
                return 'objected'
        return 'ask_for_status'
