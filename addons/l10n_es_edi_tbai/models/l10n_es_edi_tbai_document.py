import gzip
import json
import re
import math
import base64
from collections import defaultdict
from datetime import datetime
from uuid import uuid4

import requests
from lxml import etree
from pytz import timezone
from requests.exceptions import RequestException

from odoo import _, api, fields, models, release
from odoo.addons.l10n_es_edi_sii.models.account_edi_format import PatchedHTTPAdapter
from odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_agencies import get_key
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import (
    NS_MAP,
    calculate_references_digests,
    canonicalize_node,
    cleanup_xml_signature,
)
from odoo.exceptions import UserError
from odoo.tools import get_lang
from odoo.tools.float_utils import float_repr, float_round
from odoo.tools.xml_utils import cleanup_xml_node

CRC8_TABLE = [
    0x00, 0x07, 0x0E, 0x09, 0x1C, 0x1B, 0x12, 0x15, 0x38, 0x3F, 0x36, 0x31, 0x24, 0x23, 0x2A, 0x2D,
    0x70, 0x77, 0x7E, 0x79, 0x6C, 0x6B, 0x62, 0x65, 0x48, 0x4F, 0x46, 0x41, 0x54, 0x53, 0x5A, 0x5D,
    0xE0, 0xE7, 0xEE, 0xE9, 0xFC, 0xFB, 0xF2, 0xF5, 0xD8, 0xDF, 0xD6, 0xD1, 0xC4, 0xC3, 0xCA, 0xCD,
    0x90, 0x97, 0x9E, 0x99, 0x8C, 0x8B, 0x82, 0x85, 0xA8, 0xAF, 0xA6, 0xA1, 0xB4, 0xB3, 0xBA, 0xBD,
    0xC7, 0xC0, 0xC9, 0xCE, 0xDB, 0xDC, 0xD5, 0xD2, 0xFF, 0xF8, 0xF1, 0xF6, 0xE3, 0xE4, 0xED, 0xEA,
    0xB7, 0xB0, 0xB9, 0xBE, 0xAB, 0xAC, 0xA5, 0xA2, 0x8F, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9D, 0x9A,
    0x27, 0x20, 0x29, 0x2E, 0x3B, 0x3C, 0x35, 0x32, 0x1F, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0D, 0x0A,
    0x57, 0x50, 0x59, 0x5E, 0x4B, 0x4C, 0x45, 0x42, 0x6F, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7D, 0x7A,
    0x89, 0x8E, 0x87, 0x80, 0x95, 0x92, 0x9B, 0x9C, 0xB1, 0xB6, 0xBF, 0xB8, 0xAD, 0xAA, 0xA3, 0xA4,
    0xF9, 0xFE, 0xF7, 0xF0, 0xE5, 0xE2, 0xEB, 0xEC, 0xC1, 0xC6, 0xCF, 0xC8, 0xDD, 0xDA, 0xD3, 0xD4,
    0x69, 0x6E, 0x67, 0x60, 0x75, 0x72, 0x7B, 0x7C, 0x51, 0x56, 0x5F, 0x58, 0x4D, 0x4A, 0x43, 0x44,
    0x19, 0x1E, 0x17, 0x10, 0x05, 0x02, 0x0B, 0x0C, 0x21, 0x26, 0x2F, 0x28, 0x3D, 0x3A, 0x33, 0x34,
    0x4E, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5C, 0x5B, 0x76, 0x71, 0x78, 0x7F, 0x6A, 0x6D, 0x64, 0x63,
    0x3E, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2C, 0x2B, 0x06, 0x01, 0x08, 0x0F, 0x1A, 0x1D, 0x14, 0x13,
    0xAE, 0xA9, 0xA0, 0xA7, 0xB2, 0xB5, 0xBC, 0xBB, 0x96, 0x91, 0x98, 0x9F, 0x8A, 0x8D, 0x84, 0x83,
    0xDE, 0xD9, 0xD0, 0xD7, 0xC2, 0xC5, 0xCC, 0xCB, 0xE6, 0xE1, 0xE8, 0xEF, 0xFA, 0xFD, 0xF4, 0xF3
]


class L10nEsEdiTbaiDocument(models.Model):
    _name = 'l10n_es_edi_tbai.document'
    _description = 'TicketBAI Document'

    name = fields.Char(
        required=True,
        readonly=True,
    )
    date = fields.Date(
        required=True,
        readonly=True,
    )
    xml_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="XML Attachment",
        copy=False,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
    )

    state = fields.Selection([
            ('to_send', "To Send"),
            ('accepted', "Accepted"),
            ('rejected', "Rejected"),
        ],
        string="status",
        default='to_send',
        copy=False,
        readonly=True,
    )
    chain_index = fields.Integer(
        copy=False,
        readonly=True,
    )
    response_message = fields.Text(
        copy=False,
        readonly=True,
    )

    is_cancel = fields.Boolean(
        default=False,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _is_in_chain(self):
        """True iff the document has been posted to the chain and confirmed by govt."""
        return self.chain_index and self.state == 'accepted'

    def _check_can_post(self, values):
        # Ensure a certificate is available.
        if not self.company_id.l10n_es_tbai_certificate_id:
            return _("Please configure the certificate for TicketBAI.")

        # Ensure a tax agency is available.
        if not self.company_id.l10n_es_tbai_tax_agency:
            return _("Please specify a tax agency on your company for TicketBAI.")

        # Ensure a vat is available.
        if not self.company_id.vat:
            return _("Please configure the Tax ID on your company for TicketBAI.")

        if values['is_sale'] and not self.is_cancel:
            if any(not base_line['taxes'] for base_line in values['base_lines']):
                return self.env._("There should be at least one tax set on each line in order to send to TicketBAI.")

            # Chain integrity check: chain head must have been REALLY posted
            chain_head_doc = self.company_id._get_l10n_es_tbai_last_chained_document()
            if chain_head_doc and chain_head_doc != self and chain_head_doc.state != 'accepted':
                return _("TicketBAI: Cannot post invoice while chain head (%s) has not been posted", chain_head_doc.name)

            # Tax configuration check: In case of foreign customer we need the tax scope to be set
            if values['partner'] and values['partner']._l10n_es_is_foreign() and values['taxes'].filtered(lambda t: not t.tax_scope):
                return _(
                    "In case of a foreign customer, you need to configure the tax scope on taxes:\n%s",
                    "\n".join(values['taxes'].mapped('name'))
                )
            if values['is_refund']:
                refunded_doc = values['refunded_doc']
                refund_reason = values['refund_reason']
                is_simplified = values['is_simplified']

                if not refunded_doc or refunded_doc.state == 'to_send':
                    return _("TicketBAI: Cannot post a reversal document while the source document has not been posted")
                if not refund_reason:
                    return _('Refund reason must be specified (TicketBAI)')
                if is_simplified and refund_reason != 'R5':
                    return _('Refund reason must be R5 for simplified invoices (TicketBAI)')
                if not is_simplified and refund_reason == 'R5':
                    return _('Refund reason cannot be R5 for non-simplified invoices (TicketBAI)')

    # -------------------------------------------------------------------------
    # WEB SERVICE CALLS
    # -------------------------------------------------------------------------

    def _post_to_web_service(self, values):
        self.ensure_one()

        error = self._check_can_post(values)
        if error:
            return error

        if not self.xml_attachment_id:
            self._generate_xml(values)

        if (
            not self.chain_index
            and not self.is_cancel
            and values['is_sale']
        ):
            # Assign unique 'chain index' from dedicated sequence
            self.sudo().chain_index = self.company_id._get_l10n_es_tbai_next_chain_index()

        try:
            # Call the web service, retrieve and parse response
            success, response_msgs = self._post_to_agency(self.env, values['is_sale'])
        except (RequestException) as e:
            # In case of timeout / request exception
            self.sudo().response_message = e
            return

        self.sudo().response_message = '\n'.join(response_msgs)
        if success:
            self.sudo().state = 'accepted'
        else:
            self.sudo().state = 'rejected'
            self.sudo().chain_index = 0

    def _post_to_agency(self, env, is_sale):

        def _send_request_to_agency(*args, **kwargs):
            session = requests.Session()
            session.cert = kwargs.pop('pkcs12_data')
            session.mount("https://", PatchedHTTPAdapter())
            response = session.request('post', *args, **kwargs)
            response.raise_for_status()
            response_xml = None
            error = None
            if response.content:
                try:
                    response_xml = etree.fromstring(response.content)
                except etree.XMLSyntaxError as e:
                    error = str(e)
            else:
                error = self.env._('No XML response received.')
            return response.headers, response_xml, [error] if error else []

        if self.company_id.l10n_es_tbai_tax_agency in ('araba', 'gipuzkoa'):
            params = self._prepare_post_params_ar_gi()
            _response_headers, response_xml, errors = _send_request_to_agency(timeout=10, **params)
            if errors:
                return False, errors
            return self._process_post_response_xml_ar_gi(env, response_xml)

        elif self.company_id.l10n_es_tbai_tax_agency == 'bizkaia':
            params = self._prepare_post_params_bi(is_sale)
            response_headers, response_xml, errors = _send_request_to_agency(timeout=10, **params)
            if response_headers['eus-bizkaia-n3-tipo-respuesta'] != "Correcto":
                error_code = response_headers['eus-bizkaia-n3-codigo-respuesta']
                error_msg = response_headers['eus-bizkaia-n3-mensaje-respuesta']
                errors.append(error_code + ": " + error_msg)
            if errors:
                return False, errors
            return self._process_post_response_xml_bi(env, response_xml)

    def _prepare_post_params_ar_gi(self):
        """Web service parameters for Araba and Gipuzkoa."""
        company = self.company_id
        return {
            'url': get_key(self.company_id.l10n_es_tbai_tax_agency, 'cancel_url_' if self.is_cancel else 'post_url_', company.l10n_es_tbai_test_env),
            'headers': {"Content-Type": "application/xml; charset=utf-8"},
            'pkcs12_data': company.l10n_es_tbai_certificate_id,
            'data': self.xml_attachment_id.raw,
        }

    @api.model
    def _process_post_response_xml_ar_gi(self, env, response_xml):
        """Government response processing for Araba and Gipuzkoa."""
        success = int(response_xml.findtext('.//Estado')) == 0
        response_msgs = []

        # Get message in basque if env is in basque
        msg_node_name = 'Azalpena' if get_lang(env).code == 'eu_ES' else 'Descripcion'
        for res_node in response_xml.findall('.//ResultadosValidacion'):
            msg_code = res_node.findtext('Codigo')
            response_msgs.append(msg_code + ": " + res_node.findtext(msg_node_name))
            if msg_code in ('005', '019'):
                success = True  # error codes 5/19 mean XML was already received with that sequence

        return success, response_msgs

    def _prepare_post_params_bi(self, is_sale):
        """Web service parameters for Bizkaia."""

        if is_sale:
            xml_to_send = self._generate_final_xml_bi()
            lroe_str = etree.tostring(xml_to_send)
        else:
            lroe_str = self.xml_attachment_id.raw

        lroe_bytes = gzip.compress(lroe_str)

        company = self.company_id
        return {
            'url': get_key(self.company_id.l10n_es_tbai_tax_agency, 'cancel_url_' if self.is_cancel else 'post_url_', company.l10n_es_tbai_test_env),
            'headers': {
                'Accept-Encoding': 'gzip',
                'Content-Encoding': 'gzip',
                'Content-Length': str(len(lroe_str)),
                'Content-Type': 'application/octet-stream',
                'eus-bizkaia-n3-version': '1.0',
                'eus-bizkaia-n3-content-type': 'application/xml',
                'eus-bizkaia-n3-data': json.dumps({
                    'con': 'LROE',
                    'apa': '1.1' if is_sale else '2',
                    'inte': {
                        'nif': company.vat[2:] if company.vat.startswith('ES') else company.vat,
                        'nrs': self.company_id.name,
                    },
                    'drs': {
                        'mode': '240',
                        # NOTE: modelo 140 for freelancers (in/out invoices)
                        # modelo 240 for legal entities (lots of account moves ?)
                        'ejer': str(self.date.year),
                    }
                }),
            },
            'pkcs12_data': self.company_id.l10n_es_tbai_certificate_id,
            'data': lroe_bytes,
        }

    def _generate_final_xml_bi(self):
        sender = self.company_id
        lroe_values = {
            'is_emission': not self.is_cancel,
            'sender': sender,
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'fiscal_year': str(self.date.year),
        }
        lroe_values.update({'tbai_b64_list': [base64.b64encode(self.xml_attachment_id.raw).decode()]})
        lroe_str = self.env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main', lroe_values)
        lroe_xml = cleanup_xml_node(lroe_str)

        return lroe_xml

    @api.model
    def _process_post_response_xml_bi(self, env, response_xml):
        """Government response processing for Bizkaia."""
        success = response_xml.findtext('.//EstadoRegistro') == "Correcto"

        if success:
            return True, []

        error_code = response_xml.findtext('.//CodigoErrorRegistro')
        # Get message in basque if env is in basque
        error_msg_node_name = 'DescripcionErrorRegistro' + ('EU' if get_lang(env).code == 'eu_ES' else 'ES')
        error_msg = error_code + ": " + response_xml.findtext(f'.//{error_msg_node_name}', '')
        if error_code == "B4_2000003":  # already received
            success = True

        return success, [error_msg]

    # -------------------------------------------------------------------------
    # XML
    # -------------------------------------------------------------------------

    L10N_ES_TBAI_VERSION = 1.2

    def _generate_xml(self, values):
        self.ensure_one()

        def format_float(value, precision_digits=2):
            rounded_value = float_round(value, precision_digits=precision_digits)
            return float_repr(rounded_value, precision_digits=precision_digits)

        values.update({
            'doc': self,
            **self._get_header_values(),
            **self._get_sender_values(),
            **(self._get_recipient_values(values['partner']) if values['partner'] and not self.is_cancel or not values['is_sale'] else {}),
            'datetime_now': datetime.now(tz=timezone('Europe/Madrid')),
            'format_date': lambda d: datetime.strftime(d, '%d-%m-%Y'),
            'format_time': lambda d: datetime.strftime(d, '%H:%M:%S'),
            'format_float': format_float,
        })

        xml_doc = None

        if values['is_sale']:
            values.update({
                'is_emission': not self.is_cancel,
                **self.company_id._get_l10n_es_tbai_license_dict(),
                **(self._get_sale_values(values) if not self.is_cancel else {}),
            })
            xml_doc = self._generate_sale_document_xml(values)

        elif self.company_id.l10n_es_tbai_tax_agency == 'bizkaia':
            xml_doc = self._generate_purchase_document_xml_bi(values)

        if xml_doc is not None:
            self.sudo().xml_attachment_id = self.env['ir.attachment'].create({
                'name': values['attachment_name'],
                'raw': etree.tostring(xml_doc, encoding='UTF-8'),
                'type': 'binary',
                'res_model': values['res_model'],
                'res_id': values['res_id'],
            })

    @api.model
    def _get_header_values(self):
        return {
            'tbai_version': self.L10N_ES_TBAI_VERSION,
            'odoo_version': release.version,
        }

    @api.model
    def _get_sender_values(self):
        sender = self.company_id
        return {
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'sender': sender,
        }

    def _get_recipient_values(self, partner):
        recipient_values = {
            'partner': partner,
            'partner_address': ', '.join(filter(None, [partner.street, partner.street2, partner.city])),
            'alt_id_number': partner.vat or 'NO_DISPONIBLE',
        }

        if not partner._l10n_es_is_foreign() and partner.vat:
            recipient_values['nif'] = partner.vat[2:] if partner.vat.startswith('ES') else partner.vat

        elif partner.country_id in self.env.ref('base.europe').country_ids:
            recipient_values['alt_id_type'] = '02'

        else:
            recipient_values['alt_id_type'] = '04' if partner.vat else '06'
            recipient_values['alt_id_country'] = partner.country_id.code if partner.country_id else None

        return {'recipient': recipient_values}

    def _get_sale_values(self, values):
        sale_values = {
            'prev_doc': self.company_id._get_l10n_es_tbai_last_chained_document(),
            **self._get_lines_values(values['base_lines'], values['rate'], values['is_refund']),
            **self._get_regime_code_value(values['taxes'], values['is_simplified']),
        }

        if not values['partner'] or not values['partner']._l10n_es_is_foreign():
            sale_values.update(**self._get_importe_desglose_es_partner(values['base_lines'], values['is_refund']))
        else:
            sale_values.update(**self._get_importe_desglose_foreign_partner(values['base_lines'], values['is_refund']))

        return sale_values

    def _get_lines_values(self, base_lines, rate, is_refund):

        def get_base_line_price_total(base_line):
            taxes = base_line['taxes'].filtered(lambda t: t.l10n_es_type != "retencion")
            line_discount_price_unit = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
            if taxes:
                taxes_res = taxes.compute_all(
                    line_discount_price_unit,
                    quantity=base_line['quantity'],
                    currency=base_line['currency'],
                    product=base_line['product'],
                    partner=base_line['partner'],
                    is_refund=base_line['is_refund'],
                )
                return taxes_res['total_included']
            return base_line['quantity'] * line_discount_price_unit

        lines = []
        sign = -1 if is_refund else 1
        for base_line in base_lines:
            discount = base_line['price_subtotal'] - base_line['quantity'] * base_line['price_unit']
            if not any(t.l10n_es_type == 'sujeto_isp' for t in base_line['taxes']):
                total = get_base_line_price_total(base_line)
            else:
                total = base_line['price_subtotal']
            lines.append({
                'quantity': base_line['quantity'],
                'discount': -sign * (discount / rate),
                'unit_price': sign * (base_line['price_unit'] / rate) if base_line['quantity'] > 0 else 0,
                'total': sign * (total / rate),
                'description': re.sub(r'[^0-9a-zA-Z ]+', '', base_line['name'] or base_line['product'].display_name or '')[:250]
            })

        return {'lines': lines}

    def _get_regime_code_value(self, taxes, is_simplified):
        regime_key = []

        regime_key.append(taxes._l10n_es_get_regime_code())

        if is_simplified and self.company_id.l10n_es_tbai_tax_agency != 'bizkaia':
            regime_key.append('52')  # code for simplified invoices

        return {'regime_key': regime_key}

    @api.model
    def _get_importe_desglose_es_partner(self, base_lines, is_refund):
        tbai_tax_details = self._get_tbai_tax_details(base_lines, is_refund)

        sign = -1 if is_refund else 1

        tax_amount_retention = tbai_tax_details['tax_amount_retention']
        desglose = {'DesgloseFactura': tbai_tax_details['tax_details_info']}
        desglose['DesgloseFactura'].update({'S1': tbai_tax_details['S1_list'],
                                            'S2': tbai_tax_details['S2_list']})
        importe_total = round(sign * (
            tbai_tax_details['tax_details']['base_amount']
            + tbai_tax_details['tax_details']['tax_amount']
            - tax_amount_retention
        ), 2)

        return {
            'amount_total': importe_total,
            'invoice_info': desglose,
            'amount_retention': tax_amount_retention * -sign,
        }

    @api.model
    def _get_importe_desglose_foreign_partner(self, base_lines, is_refund):
        tbai_tax_details_service = self._get_tbai_tax_details(
            base_lines,
            is_refund,
            filter_invl_to_apply=lambda base_line: any(t.tax_scope == 'service' for t in base_line['taxes'])
        )
        tbai_tax_details_consu = self._get_tbai_tax_details(
            base_lines,
            is_refund,
            filter_invl_to_apply=lambda base_line: any(t.tax_scope == 'consu' for t in base_line['taxes'])
        )

        sign = -1 if is_refund else 1

        service_retention = tbai_tax_details_service['tax_amount_retention']
        consu_retention = tbai_tax_details_consu['tax_amount_retention']
        desglose = {}
        if tbai_tax_details_service['tax_details_info']:
            desglose.setdefault('DesgloseTipoOperacion', {})
            desglose['DesgloseTipoOperacion']['PrestacionServicios'] = tbai_tax_details_service['tax_details_info']
            desglose['DesgloseTipoOperacion']['PrestacionServicios'].update(
                {'S1': tbai_tax_details_service['S1_list'],
                    'S2': tbai_tax_details_service['S2_list']})

        if tbai_tax_details_consu['tax_details_info']:
            desglose.setdefault('DesgloseTipoOperacion', {})
            desglose['DesgloseTipoOperacion']['Entrega'] = tbai_tax_details_consu['tax_details_info']
            desglose['DesgloseTipoOperacion']['Entrega'].update(
                {'S1': tbai_tax_details_consu['S1_list'],
                    'S2': tbai_tax_details_consu['S2_list']})
        importe_total = round(sign * (
            tbai_tax_details_service['tax_details']['base_amount']
            + tbai_tax_details_service['tax_details']['tax_amount']
            - service_retention
            + tbai_tax_details_consu['tax_details']['base_amount']
            + tbai_tax_details_consu['tax_details']['tax_amount']
            - consu_retention
        ), 2)
        tax_amount_retention = service_retention + consu_retention

        return {
            'amount_total': importe_total,
            'invoice_info': desglose,
            'amount_retention': tax_amount_retention * -sign,
        }

    def _get_tbai_tax_details(self, base_lines, is_refund, filter_invl_to_apply=None):

        tax_details = self.get_tax_details(base_lines, filter_invl_to_apply=filter_invl_to_apply)

        recargo_tax_details = self.get_recargo_tax_details(base_lines, tax_details, filter_invl_to_apply=filter_invl_to_apply)

        sign = -1 if is_refund else 1

        tax_details_info = defaultdict(dict)

        tax_amount_deductible = 0.0
        tax_amount_retention = 0.0
        base_amount_not_subject = 0.0
        base_amount_not_subject_loc = 0.0
        tax_subject_info_list = []
        tax_subject_isp_info_list = []
        for tax_values in tax_details['tax_details'].values():

            if tax_values['l10n_es_type'] in ('sujeto', 'sujeto_isp'):
                tax_amount_deductible += tax_values['tax_amount']

                base_amount = sign * tax_values['base_amount']
                tax_info = {
                    'TipoImpositivo': tax_values['applied_tax_amount'],
                    'BaseImponible': float_round(base_amount, 2),
                    'CuotaRepercutida': float_round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                }

                recargo = recargo_tax_details.get(tax_values['group_tax_details'][0]['tax_repartition_line'].tax_id)
                if recargo:
                    tax_info['CuotaRecargoEquivalencia'] = float_round(sign * recargo['tax_amount'], 2)
                    tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']

                if tax_values['l10n_es_type'] == 'sujeto':
                    tax_subject_info_list.append(tax_info)
                else:
                    tax_subject_isp_info_list.append(tax_info)

            elif tax_values['l10n_es_type'] == 'exento':
                tax_details_info['Sujeta'].setdefault('Exenta', {'DetalleExenta': []})
                tax_details_info['Sujeta']['Exenta']['DetalleExenta'].append({
                    'BaseImponible': float_round(sign * tax_values['base_amount'], 2),
                    'CausaExencion': tax_values['l10n_es_exempt_reason'],
                })
            elif tax_values['l10n_es_type'] == 'retencion':
                tax_amount_retention += tax_values['tax_amount']
            elif tax_values['l10n_es_type'] == 'no_sujeto':
                base_amount_not_subject += tax_values['base_amount']
            elif tax_values['l10n_es_type'] == 'no_sujeto_loc':
                base_amount_not_subject_loc += tax_values['base_amount']

        if tax_subject_isp_info_list and not tax_subject_info_list:  # Only for sale_invoices
            tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S2'}
        elif not tax_subject_isp_info_list and tax_subject_info_list:
            tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S1'}
        elif tax_subject_isp_info_list and tax_subject_info_list:
            tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S3'}

        if tax_subject_info_list:
            tax_details_info['Sujeta']['NoExenta'].setdefault('DesgloseIVA', {})
            tax_details_info['Sujeta']['NoExenta']['DesgloseIVA'].setdefault('DetalleIVA', [])
            tax_details_info['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'] += tax_subject_info_list
        if tax_subject_isp_info_list:
            tax_details_info['Sujeta']['NoExenta'].setdefault('DesgloseIVA', {})
            tax_details_info['Sujeta']['NoExenta']['DesgloseIVA'].setdefault('DetalleIVA', [])
            tax_details_info['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'] += tax_subject_isp_info_list

        if not self.company_id.currency_id.is_zero(base_amount_not_subject):
            tax_details_info['NoSujeta']['ImportePorArticulos7_14_Otros'] = float_round(sign * base_amount_not_subject, 2)
        if not self.company_id.currency_id.is_zero(base_amount_not_subject_loc):
            tax_details_info['NoSujeta']['ImporteTAIReglasLocalizacion'] = float_round(sign * base_amount_not_subject_loc, 2)

        return {
            'tax_details': tax_details,
            'tax_details_info': tax_details_info,
            'tax_amount_deductible': tax_amount_deductible,
            'tax_amount_retention': tax_amount_retention,
            'base_amount_not_subject': base_amount_not_subject,
            'S1_list': tax_subject_info_list,
            'S2_list': tax_subject_isp_info_list,
        }

    def get_tax_details(self, base_lines, filter_invl_to_apply=None):

        def filter_tax_values_to_apply(base_line, tax_values):
            # For intra-community, we do not take into account the negative repartition line
            return (
                tax_values['tax_repartition_line'].factor_percent > 0.0
                and tax_values['tax_repartition_line'].tax_id.amount != -100.0
            )

        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id
            return {
                'applied_tax_amount': tax.amount,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_exempt_reason': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
            }

        to_process = []
        base_lines_full_filtered = [base_line for base_line in base_lines if filter_invl_to_apply(base_line)] if filter_invl_to_apply else base_lines
        for base_line in base_lines_full_filtered:
            tax_details_results = self.env['account.tax']._prepare_base_line_tax_details(base_line, self.company_id)
            to_process.append((base_line, tax_details_results))

        return self.env['account.tax']._aggregate_taxes(
            to_process,
            self.company_id,
            filter_tax_values_to_apply=filter_tax_values_to_apply,
            grouping_key_generator=grouping_key_generator,
        )

    def get_recargo_tax_details(self, base_lines, tax_details, filter_invl_to_apply=None):
        # Detect for which is the main tax for 'recargo'. Since only a single combination tax + recargo is allowed
        # on the same invoice, this can be deduced globally.

        recargo_tax_details = {}  # Mapping between main tax and recargo tax details

        base_lines_filtered = [base_line for base_line in base_lines if filter_invl_to_apply(base_line)] if filter_invl_to_apply else base_lines
        for base_line in base_lines_filtered:
            taxes = base_line['taxes'].flatten_taxes_hierarchy()
            recargo_tax = [t for t in taxes if t.l10n_es_type == 'recargo']
            if recargo_tax:
                recargo_main_tax = taxes.filtered(lambda x: x.l10n_es_type in ('sujeto', 'sujeto_isp'))[:1]
                if not recargo_tax_details.get(recargo_main_tax):
                    recargo_tax_details[recargo_main_tax] = next(
                        x for x in tax_details['tax_details'].values()
                        if x['group_tax_details'][0]['tax_repartition_line'].tax_id == recargo_tax[0]
                    )

        return recargo_tax_details

    def _generate_sale_document_xml(self, values):
        template_name = 'l10n_es_edi_tbai.template_invoice_main' + ('_cancel' if self.is_cancel else '_post')
        xml_str = self.env['ir.qweb']._render(template_name, values)
        xml_doc = cleanup_xml_node(xml_str, remove_blank_nodes=False)

        try:
            xml_doc = self._sign_sale_document(xml_doc)
        except ValueError:
            raise UserError(_('No valid certificate found for this company, TicketBAI file will not be signed.\n'))

        return xml_doc

    def _sign_sale_document(self, xml_root):
        self.ensure_one()

        company = self.company_id
        certificate_sudo = company.sudo().l10n_es_tbai_certificate_id
        if not certificate_sudo:
            raise UserError(_('No certificate found'))

        # Identifiers
        document_id = "Document-" + str(uuid4())
        signature_id = "Signature-" + document_id
        keyinfo_id = "KeyInfo-" + document_id
        sigproperties_id = "SignatureProperties-" + document_id

        # Render digital signature scaffold from QWeb

        e, n = certificate_sudo._get_public_key_numbers_bytes()
        issuer = certificate_sudo._l10n_es_edi_tbai_get_issuer()

        values = {
            'dsig': {
                'document_id': document_id,
                'x509_certificate': base64.encodebytes(base64.b64decode(certificate_sudo._get_der_certificate_bytes())).decode(),
                'public_modulus': n.decode(),
                'public_exponent': e.decode(),
                'iso_now': datetime.now().isoformat(),
                'keyinfo_id': keyinfo_id,
                'signature_id': signature_id,
                'sigproperties_id': sigproperties_id,
                'reference_uri': "Reference-" + document_id,
                'sigpolicy_url': get_key(company.l10n_es_tbai_tax_agency, 'sigpolicy_url'),
                'sigpolicy_digest': get_key(company.l10n_es_tbai_tax_agency, 'sigpolicy_digest'),
                'sigcertif_digest': certificate_sudo._get_fingerprint_bytes(formatting='base64').decode(),
                'x509_issuer_description': issuer,
                'x509_serial_number': int(certificate_sudo.serial_number),
            }
        }
        xml_sig_str = self.env['ir.qweb']._render('l10n_es_edi_tbai.template_digital_signature', values)
        xml_sig = cleanup_xml_signature(xml_sig_str)

        # Complete document with signature template
        xml_root.append(xml_sig)

        # Compute digest values for references
        calculate_references_digests(xml_sig.find("SignedInfo", namespaces=NS_MAP))

        # Sign (writes into SignatureValue)
        signed_info_xml = xml_sig.find('SignedInfo', namespaces=NS_MAP)
        xml_sig.find('SignatureValue', namespaces=NS_MAP).text = certificate_sudo._sign(canonicalize_node(signed_info_xml)).decode()

        return xml_root

    def _generate_purchase_document_xml_bi(self, values):
        sender = self.company_id
        lroe_values = {
            'is_emission': not self.is_cancel,
            'sender': sender,
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'fiscal_year': str(self.date.year),
        }
        lroe_values.update(values)
        lroe_str = self.env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main_recibidas', lroe_values)
        lroe_xml = cleanup_xml_node(lroe_str)

        return lroe_xml

    # -------------------------------------------------------------------------
    # SIGNATURE AND QR CODE
    # -------------------------------------------------------------------------

    @api.model
    def _get_tbai_sequence_and_number(self):
        """Get the TicketBAI sequence a number values for this invoice."""
        self.ensure_one()

        matching = list(re.finditer(r'\d+', self.name))[-1]
        sequence_prefix = self.name[:matching.start()]
        sequence_number = int(matching.group())

        # NOTE non-decimal characters should not appear in the number
        seq_length = self.env['sequence.mixin']._get_sequence_format_param(self.name)[1]['seq_length']
        number = f"{sequence_number:0{seq_length}d}"

        sequence = sequence_prefix.rstrip('/')
        sequence = re.sub(r"[^0-9A-Za-z.\_\-\/]+", "", sequence)  # remove forbidden characters
        sequence = re.sub(r"\s+", " ", sequence)  # no more than one consecutive whitespace allowed
        # NOTE (optional) not recommended to use chars out of ([0123456789ABCDEFGHJKLMNPQRSTUVXYZ.\_\-\/ ])
        sequence += "TEST" if self.company_id.l10n_es_tbai_test_env else ""
        return sequence, number

    def _get_tbai_signature_and_date(self):
        """
        Get the TicketBAI signature and registration date for this document.
        Should only be called for a "post" document (is_cancel==False).
        The registration date is the date the document was registered into the govt's TicketBAI servers.
        """
        self.ensure_one()
        vals = self._get_values_from_xml({
            'signature': './/{http://www.w3.org/2000/09/xmldsig#}SignatureValue',
            'registration_date': './/CabeceraFactura//FechaExpedicionFactura'
        })
        # RFC2045 - Base64 Content-Transfer-Encoding (page 25)
        # Any characters outside of the base64 alphabet are to be ignored in base64-encoded data.
        signature = vals['signature'].replace("\n", "")
        registration_date = datetime.strptime(vals['registration_date'], '%d-%m-%Y')
        return signature, registration_date

    def _get_tbai_id(self):
        """Get the TicketBAI ID (TBAID) as defined in the TicketBAI doc."""
        self.ensure_one()
        if not self._is_in_chain():
            return ''

        signature, registration_date = self._get_tbai_signature_and_date()
        company = self.company_id
        tbai_id_no_crc = '-'.join([
            'TBAI',
            str(company.vat[2:] if company.vat.startswith('ES') else company.vat),
            datetime.strftime(registration_date, '%d%m%y'),
            signature[:13],
            ''  # CRC
        ])
        return tbai_id_no_crc + self._get_crc8(tbai_id_no_crc)

    def _get_tbai_qr(self):
        """Returns the URL for the document's QR code.  We can not use url_encode because it escapes / e.g."""
        self.ensure_one()
        if not self._is_in_chain():
            return ''

        company = self.company_id
        sequence, number = self._get_tbai_sequence_and_number()
        tbai_qr_no_crc = get_key(company.l10n_es_tbai_tax_agency, 'qr_url_', company.l10n_es_tbai_test_env) + '?' + '&'.join([
            'id=' + self._get_tbai_id(),
            's=' + sequence,
            'nf=' + number,
            'i=' + self._get_values_from_xml({'importe': './/ImporteTotalFactura'})['importe']
        ])
        qr_url = tbai_qr_no_crc + '&cr=' + self._get_crc8(tbai_qr_no_crc)
        return qr_url

    def _get_crc8(self, data):
        crc = 0x0
        for c in data:
            crc = CRC8_TABLE[(crc ^ ord(c)) & 0xFF]
        return f'{crc & 0xFF:03d}'

    def _get_values_from_xml(self, xpaths):
        """This function reads values directly from the 'post' XML submitted to the government"""
        res = dict.fromkeys(xpaths, '')
        doc_xml = self._get_xml()
        if doc_xml is None:
            return res
        for key, value in xpaths.items():
            res[key] = doc_xml.find(value).text
        return res

    def _get_xml(self):
        """Returns the XML object representing the document."""
        self.ensure_one()
        doc = self.xml_attachment_id
        if not doc:
            return None
        return etree.fromstring(doc.raw.decode('utf-8'))
