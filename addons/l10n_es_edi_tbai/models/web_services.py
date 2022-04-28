# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gzip
import io
import json
from base64 import b64encode

import requests
from lxml import etree
from odoo.addons.l10n_es_edi_sii.models.account_edi_format import PatchedHTTPAdapter
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import L10nEsTbaiXmlUtils
from odoo.tools import get_lang

# -------------------------------------------------------------------------
# TICKETBAI WEB SERVICES
# -------------------------------------------------------------------------

TBAI_VERSION = 1.2

def get_web_services_for_agency(agency, env):
    """
    Factory method to instantiate the sub-class of TicketBaiWebServices corresponding
    to the given agency.
    """
    if agency == 'araba':
        return ArabaWebServices(env)
    elif agency == 'bizkaia':
        return BizkaiaWebServices(env)
    elif agency == 'gipuzkoa':
        return GipuzkoaWebServices(env)
    raise ValueError(f"No known tax agency with name {agency} (TicketBAI)")

class TicketBaiWebServices():
    """Provides helper methods for interacting with the Bask country's TicketBai servers."""

    URLS = {}

    def __init__(self, env):
        self.env = env

    def post(self, invoice, invoice_xml, cancel=False):
        params = self._prepare_post_params(invoice, invoice_xml, cancel)
        response = self._post(timeout=10, **params)
        return self._process_post_response(response)

    def _prepare_post_params(self, invoice, invoice_xml, cancel=False):
        raise NotImplementedError()

    def _post(self, *args, **kwargs):
        session = requests.Session()
        session.cert = kwargs.pop('pkcs12_data')
        session.mount("https://", PatchedHTTPAdapter())
        return session.request('post', *args, **kwargs)

    def _process_post_response(self, response):
        raise NotImplementedError()

    def _get_url(self, key, company=None):
        # Keys ending with '_' have two variants: 'test' and 'prod'
        if key.endswith('_'):
            key += 'test' if company.l10n_es_edi_test_env else 'prod'
        return self.URLS[key]

    def get_sigpolicy_url(self):
        return self._get_url('sigpolicy')

    def get_sigpolicy_digest(self):
        return self._get_url('sigpolicy_digest')

    def get_xsd_urls(self):
        """
        Araba and Gipuzkoa each have a single URL pointing to a zip file (which may contain more than those two XSDs)
        Bizkaia has two URLs (one for each XSD): in that case a tuple of strings is returned (instead of a single string)
        """
        return self._get_url('xsd')

    def get_emission_url(self, company):
        return self._get_url(key='invoice_', company=company)

    def get_cancellation_url(self, company):
        return self._get_url(key='cancel_', company=company)

    def get_qr_base_url(self, company):
        return self._get_url(key='qr_', company=company)

class ArabaWebServices(TicketBaiWebServices):

    URLS = {
        'sigpolicy': 'https://ticketbai.araba.eus/tbai/sinadura/',
        'sigpolicy_digest': 'd69VEBc4ED4QbwnDtCA2JESgJiw+rwzfutcaSl5gYvM=',
        'xsd': 'https://web.araba.eus/documents/105044/5608600/TicketBai12+%282%29.zip',
        'invoice_test': 'https://pruebas-ticketbai.araba.eus/TicketBAI/v1/facturas/',
        'invoice_prod': 'https://ticketbai.araba.eus/TicketBAI/v1/facturas/',
        'qr_test': 'https://pruebas-ticketbai.araba.eus/tbai/qrtbai/',
        'qr_prod': 'https://ticketbai.araba.eus/tbai/qrtbai/',
        'cancel_test': 'https://pruebas-ticketbai.araba.eus/TicketBAI/v1/anulaciones/',
        'cancel_prod': 'https://ticketbai.araba.eus/TicketBAI/v1/anulaciones/',
    }

    def _prepare_post_params(self, invoice, invoice_xml, cancel=False):
        company = invoice.company_id
        return {
            'url': self.get_cancellation_url(company) if cancel else self.get_emission_url(company),
            'headers': {"Content-Type": "application/xml; charset=utf-8"},
            'pkcs12_data': company.l10n_es_tbai_certificate_id,
            'data': etree.tostring(invoice_xml, encoding='UTF-8'),
        }

    def _process_post_response(self, response):
        response_data = response.content.decode(response.encoding)
        try:
            response_xml = etree.fromstring(bytes(response_data, 'utf-8'))
        except etree.XMLSyntaxError as e:
            return False, e, response_xml

        # Error management
        message = ''
        already_received = False
        # Get message in basque if env is in basque
        msg_node_name = 'Azalpena' if get_lang(self.env).code == 'eu_ES' else 'Descripcion'
        for xml_res_node in response_xml.findall(r'.//ResultadosValidacion'):
            message_code = xml_res_node.find('Codigo').text
            message += message_code + ": " + xml_res_node.find(msg_node_name).text + "\n"
            if message_code in ('005', '019'):
                already_received = True  # error codes 5/19 mean XML was already received with that sequence
        response_code = int(response_xml.find(r'.//Estado').text)
        response_success = (response_code == 0) or already_received

        return response_success, message, response_xml


class BizkaiaWebServices(TicketBaiWebServices):

    URLS = {
        'sigpolicy': 'https://www.batuz.eus/fitxategiak/batuz/ticketbai/sinadura_elektronikoaren_zehaztapenak_especificaciones_de_la_firma_electronica_v1_0.pdf',
        'sigpolicy_digest': 'Quzn98x3PMbSHwbUzaj5f5KOpiH0u8bvmwbbbNkO9Es=',
        'xsd': (
            'https://www.batuz.eus/fitxategiak/batuz/ticketbai/Anula_ticketBaiV1-2.xsd',
            'https://www.batuz.eus/fitxategiak/batuz/ticketbai/ticketBaiV1-2.xsd',
        ),
        'invoice_test': 'https://pruesarrerak.bizkaia.eus/N3B4000M/aurkezpena',
        'invoice_prod': 'https://sarrerak.bizkaia.eus/N3B4000M/aurkezpena',
        'qr_test': 'https://batuz.eus/QRTBAI/',
        'qr_prod': 'https://batuz.eus/QRTBAI/',
        'cancel_test': 'https://pruesarrerak.bizkaia.eus/N3B4000M/aurkezpena',
        'cancel_prod': 'https://sarrerak.bizkaia.eus/N3B4000M/aurkezpena',
    }

    def _prepare_post_params(self, invoice, invoice_xml, cancel=False):
        sender = invoice.company_id
        lroe_values = {
            'is_submission': not cancel,
            'sender': sender,
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'tbai_b64_list': [b64encode(etree.tostring(invoice_xml, encoding="UTF-8")).decode()],
            'fiscal_year': str(invoice.date.year),
        }
        lroe_str = self.env.ref('l10n_es_edi_tbai.template_LROE_240_main')._render(lroe_values)
        invoice_xml = L10nEsTbaiXmlUtils._cleanup_xml_content(lroe_str)
        xml_str = etree.tostring(invoice_xml, encoding="UTF-8")  # TODO save as EDI document

        xml_bytes = io.BytesIO()
        with gzip.GzipFile(mode="wb", fileobj=xml_bytes) as xml_gz:
            xml_gz.write(xml_str)
        xml_bytes = xml_bytes.getvalue()

        company = invoice.company_id
        return {
            'url': self.get_cancellation_url(company) if cancel else self.get_emission_url(company),
            'headers': {
                'Accept-Encoding': 'gzip',
                'Content-Encoding': 'gzip',
                'Content-Length': str(len(xml_str)),
                'Content-Type': 'application/octet-stream',
                'eus-bizkaia-n3-version': '1.0',
                'eus-bizkaia-n3-content-type': 'application/xml',
                'eus-bizkaia-n3-data': json.dumps({
                    'con': 'LROE',
                    'apa': '1.1',
                    'inte': {
                        'nif': lroe_values['sender_vat'],
                        'nrs': sender.name,
                    },
                    'drs': {
                        'mode': '240',
                        'ejer': '2022',
                    }
                }),
            },
            'pkcs12_data': invoice.company_id.l10n_es_tbai_certificate_id,
            'data': xml_bytes,
        }

    def _process_post_response(self, response):
        response_data = response.content.decode(response.encoding)
        try:
            response_xml = etree.fromstring(bytes(response_data, 'utf-8'))
        except etree.XMLSyntaxError as e:
            return False, e, response_xml

        # GLOBAL STATUS (batch)
        # message = response.headers['eus-bizkaia-n3-mensaje-respuesta']
        # response_code = response.headers['eus-bizkaia-n3-tipo-respuesta']
        # response_success = (response_code == "Correcto")

        # INVOICE STATUS (only one in batch)
        # Get message in basque if env is in basque
        msg_node_name = 'DescripcionErrorRegistro' + ('EU' if get_lang(self.env).code == 'eu_ES' else 'ES')
        response_success = response_xml.find(r'.//EstadoRegistro').text == "Correcto"
        message = ''
        if not response_success:
            response_code = response_xml.find(r'.//CodigoErrorRegistro').text
            if response_code == "B4_2000003":  # already received
                response_success = True
            message = response_code + ": " + (response_xml.find(rf'.//{msg_node_name}').text or '')
        return response_success, message, response_xml


class GipuzkoaWebServices(ArabaWebServices):

    URLS = {
        'sigpolicy': 'https://www.gipuzkoa.eus/TicketBAI/signature',
        'sigpolicy_digest': '6NrKAm60o7u62FUQwzZew24ra2ve9PRQYwC21AM6In0=',
        'xsd': 'https://www.gipuzkoa.eus/documents/2456431/13761107/Esquemas+de+archivos+XSD+de+env%C3%ADo+y+anulaci%C3%B3n+de+factura_1_2.zip',
        'invoice_test': 'https://tbai-prep.egoitza.gipuzkoa.eus/WAS/HACI/HTBRecepcionFacturasWEB/rest/recepcionFacturas/alta',
        'invoice_prod': 'https://tbai-z.egoitza.gipuzkoa.eus/sarrerak/alta',
        'qr_test': 'https://tbai.prep.gipuzkoa.eus/qr/',
        'qr_prod': 'https://tbai.egoitza.gipuzkoa.eus/qr/',
        'cancel_test': 'https://tbai-prep.egoitza.gipuzkoa.eus/WAS/HACI/HTBRecepcionFacturasWEB/rest/recepcionFacturas/anulacion',
        'cancel_prod': 'https://tbai-z.egoitza.gipuzkoa.eus/sarrerak/baja',
    }
