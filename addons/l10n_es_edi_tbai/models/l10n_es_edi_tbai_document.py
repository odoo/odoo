import gzip
import json
import re
import base64
from datetime import datetime
from uuid import uuid4

import requests
from lxml import etree
from pytz import timezone
from requests.exceptions import RequestException

from odoo import _, api, fields, models, release
from odoo.addons.certificate.tools import CertificateAdapter
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

        if self.company_id.l10n_es_tbai_tax_agency == 'bizkaia' and self.company_id._l10n_es_freelancer() and not self.env['ir.config_parameter'].sudo().get_param('l10n_es_edi_tbai.epigrafe', False):
            return _("In order to use Ticketbai Batuz for freelancers, you will need to configure the "
                        "Epigrafe or Main Activity.  In this version, you need to go in debug mode to "
                        "Settings > Technical > System Parameters and set the parameter 'l10n_es_edi_tbai.epigrafe'"
                        "to your epigrafe number. You can find them in %s",
                        "https://www.batuz.eus/fitxategiak/batuz/lroe/batuz_lroe_lista_epigrafes_v1_0_3.xlsx")

        if values['is_sale'] and not self.is_cancel:
            if any(not base_line['tax_ids'] for base_line in values['base_lines']):
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
                refunded_doc_invoice_date = values['refunded_doc_invoice_date']
                is_simplified = values['is_simplified']

                if not refunded_doc or refunded_doc.state == 'to_send':
                    invoice_sent_before_original = True
                    if not refunded_doc and refunded_doc_invoice_date:
                        domain = [('date', '<', refunded_doc_invoice_date),
                                  ('company_id', '=', self.company_id.id),
                                  ('chain_index', '!=', 0)]
                        invoice_sent_before_original = self.search(domain, order="date", limit=1)
                    if invoice_sent_before_original:  # No error if the original invoice was imported from a previous system
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
            session.mount("https://", CertificateAdapter())
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
            success, errors_add = self._process_post_response_xml_bi(env, response_xml)
            errors += errors_add
            return success, errors

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
        company = self.company_id
        freelancer = company._l10n_es_freelancer()

        if is_sale:
            xml_to_send = self._generate_final_xml_bi(freelancer=freelancer)
            lroe_str = etree.tostring(xml_to_send)
        else:
            lroe_str = self.xml_attachment_id.raw

        lroe_bytes = gzip.compress(lroe_str)


        return {
            'url': get_key(company.l10n_es_tbai_tax_agency, 'cancel_url_' if self.is_cancel else 'post_url_', company.l10n_es_tbai_test_env),
            'headers': {
                'Accept-Encoding': 'gzip',
                'Content-Encoding': 'gzip',
                'Content-Length': str(len(lroe_str)),
                'Content-Type': 'application/octet-stream',
                'eus-bizkaia-n3-version': '1.0',
                'eus-bizkaia-n3-content-type': 'application/xml',
                'eus-bizkaia-n3-data': json.dumps({
                    'con': 'LROE',
                    'apa': '2.1' if freelancer and not is_sale else '1.1' if is_sale else '2',
                    'inte': {
                        'nif': company.vat[2:] if company.vat.startswith('ES') else company.vat,
                        'nrs': company.name,
                    },
                    'drs': {
                        'mode': '140' if freelancer else '240',
                        'ejer': str(self.date.year),
                    }
                }),
            },
            'pkcs12_data': company.l10n_es_tbai_certificate_id,
            'data': lroe_bytes,
        }

    def _generate_final_xml_bi(self, freelancer=False):
        sender = self.company_id
        lroe_values = {
            'is_emission': not self.is_cancel,
            'sender': sender,
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'fiscal_year': str(self.date.year),
            'freelancer': freelancer,
            'is_freelancer': freelancer,  # For bugfix, will be removed in master
            'epigrafe': self.env['ir.config_parameter'].sudo().get_param('l10n_es_edi_tbai.epigrafe', '')
        }
        lroe_values.update({'tbai_b64_list': [base64.b64encode(self.xml_attachment_id.raw).decode()]})
        lroe_str = self.env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main', lroe_values)
        lroe_xml = cleanup_xml_node(lroe_str)

        return lroe_xml

    @api.model
    def _process_post_response_xml_bi(self, env, response_xml):
        """Government response processing for Bizkaia."""
        if response_xml is None:
            return False, []
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
            **(self._get_recipient_values(values['partner'], values["is_simplified"]) if values['partner'] and not self.is_cancel or not values['is_sale'] else {}),
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
            company = self.company_id
            freelancer = company._l10n_es_freelancer()
            values.update({'freelancer': freelancer})
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

    def _get_recipient_values(self, partner, is_simplified=False):
        # TicketBAI accept recipient data for simplified invoices,
        # but only if the partner has a VAT number
        if is_simplified and not partner.vat:
            return {}
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

    def _get_refunded_values(self, values):
        if not values.get('is_refund'):
            return {}
        refunded_doc = values['refunded_doc']
        refunded_name = values['refunded_name']
        if refunded_doc:
            sequence, number = refunded_doc._get_tbai_sequence_and_number()
        else:
            sequence, number = self._get_tbai_seq_from_name(refunded_name)
        return {
            'refunded_serie': sequence,
            'refunded_num': number,
            'refunded_date': values['refunded_doc_invoice_date'],
        }

    def _get_sale_values(self, values):
        sale_values = {
            'chain_prev_document': self.company_id._get_l10n_es_tbai_last_chained_document(),
            **self._get_regime_code_value(values['taxes'], values['is_simplified']),
            **self._get_refunded_values(values),
        }

        if not values['partner'] or not values['partner']._l10n_es_is_foreign() or values["is_simplified"]:
            sale_values.update(**self._get_importe_desglose_es_partner(values['base_lines'], values['is_refund']))
        else:
            sale_values.update(**self._get_importe_desglose_foreign_partner(values['base_lines'], values['is_refund']))

        return sale_values

    def _get_regime_code_value(self, taxes, is_simplified):
        return {'regime_key': [taxes._l10n_es_get_regime_code()]}

    @api.model
    def _add_base_lines_tax_amounts(self, base_lines, company, tax_lines=None):
        AccountTax = self.env['account.tax']
        AccountTax._add_tax_details_in_base_lines(base_lines, company)
        AccountTax._round_base_lines_tax_details(base_lines, company, tax_lines=tax_lines)

        for base_line in base_lines:
            discount = base_line['discount']
            price_unit = base_line['price_unit'] / base_line['rate'] if base_line['rate'] else 0.0
            quantity = base_line['quantity']
            price_subtotal = base_line['price_subtotal'] = base_line['tax_details']['raw_total_excluded']
            base_line['price_total'] = base_line['tax_details']['raw_total_included']
            for tax_data in base_line['tax_details']['taxes_data']:
                if tax_data['tax'].l10n_es_type == 'retencion':
                    base_line['price_total'] -= tax_data['tax_amount']

            if discount == 100.0:
                gross_price_subtotal_before_discount = price_unit * quantity
            else:
                gross_price_subtotal_before_discount = price_subtotal / (1 - discount / 100.0)

            base_line['gross_price_subtotal'] = gross_price_subtotal_before_discount
            base_line['discount_amount'] = gross_price_subtotal_before_discount - price_subtotal
            base_line['description'] = re.sub(r'[^0-9a-zA-Z ]+', '', base_line['name'] or base_line['product_id'].display_name or '')[:250]

            if quantity:
                base_line['gross_price_unit'] = gross_price_subtotal_before_discount / quantity
            else:
                base_line['gross_price_unit'] = 0.0

    @api.model
    def _build_tax_details_info(self, values_list):
        sujeta_no_sujeta = {}
        sujeto = []
        sujeto_isp = []
        encountered_l10n_es_type = set()
        for values in values_list:
            grouping_key = values['grouping_key']
            if not grouping_key:
                continue

            l10n_es_type = grouping_key['l10n_es_type']
            sign = grouping_key['is_refund'] and -1 or 1
            encountered_l10n_es_type.add(l10n_es_type)
            if l10n_es_type in ('sujeto', 'sujeto_isp'):
                tax_info = {
                    'TipoImpositivo': grouping_key['applied_tax_amount'],
                    'BaseImponible': sign * float_round(values['base_amount'], 2),
                    'CuotaRepercutida': sign * float_round(values['tax_amount'], 2),
                }
                sujeta_no_sujeta\
                    .setdefault('Sujeta', {})\
                    .setdefault('NoExenta', {})\
                    .setdefault('DesgloseIVA', {'DetalleIVA': []})['DetalleIVA']\
                    .append(tax_info)
                if l10n_es_type == 'sujeto':
                    sujeto.append(tax_info)
                else:
                    sujeto_isp.append(tax_info)
            elif l10n_es_type == 'exento':
                sujeta_no_sujeta\
                    .setdefault('Sujeta', {})\
                    .setdefault('Exenta', {'DetalleExenta': []})['DetalleExenta']\
                    .append({
                        'BaseImponible': sign * float_round(values['base_amount'], 2),
                        'CausaExencion': grouping_key['l10n_es_exempt_reason'],
                    })
            elif l10n_es_type == 'recargo':
                detalle_iva = sujeta_no_sujeta\
                    .get('Sujeta', {})\
                    .get('NoExenta', {})\
                    .get('DesgloseIVA', {})\
                    .get('DetalleIVA')
                if detalle_iva:
                    detalle_iva[-1]['CuotaRecargoEquivalencia'] = sign * float_round(values['tax_amount'], 2)
                    detalle_iva[-1]['TipoRecargoEquivalencia'] = sign * grouping_key['applied_tax_amount']
            elif l10n_es_type == 'no_sujeto':
                no_sujeta = sujeta_no_sujeta.setdefault('NoSujeta', {})
                no_sujeta.setdefault('ImportePorArticulos7_14_Otros', 0.0)
                no_sujeta['ImportePorArticulos7_14_Otros'] += sign * float_round(values['base_amount'], 2)
            elif l10n_es_type == 'no_sujeto_loc':
                no_sujeta = sujeta_no_sujeta.setdefault('NoSujeta', {})
                no_sujeta.setdefault('ImporteTAIReglasLocalizacion', 0.0)
                no_sujeta['ImporteTAIReglasLocalizacion'] += sign * float_round(values['base_amount'], 2)

        if 'sujeto' in encountered_l10n_es_type and 'sujeto_isp' not in encountered_l10n_es_type:
            sujeta_no_sujeta['Sujeta']['NoExenta']['TipoNoExenta'] = 'S2'
        elif 'sujeto' not in encountered_l10n_es_type and 'sujeto_isp' in encountered_l10n_es_type:
            sujeta_no_sujeta['Sujeta']['NoExenta']['TipoNoExenta'] = 'S1'
        elif 'sujeto' in encountered_l10n_es_type and 'sujeto_isp' in encountered_l10n_es_type:
            sujeta_no_sujeta['Sujeta']['NoExenta']['TipoNoExenta'] = 'S3'

        return {
            'sujeta_no_sujeta': sujeta_no_sujeta,
            'sujeto': sujeto,
            'sujeto_isp': sujeto_isp,
        }

    @api.model
    def _get_importe_desglose_es_partner(self, base_lines, is_refund):
        AccountTax = self.env['account.tax']

        def tax_details_info_grouping_function(base_line, tax_data):
            if not tax_data:
                return None
            tax = tax_data['tax']

            return {
                'applied_tax_amount': tax.amount,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_exempt_reason': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'is_reverse_charge': tax_data['is_reverse_charge'],
                'tax_scope': tax.tax_scope,
                'is_refund': base_line['is_refund'],
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, tax_details_info_grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)

        tax_details_info = self._build_tax_details_info(values_per_grouping_key.values())
        invoice_info = {
            'DesgloseFactura': {
                **tax_details_info['sujeta_no_sujeta'],
                'S1': tax_details_info['sujeto'],
                'S2': tax_details_info['sujeto_isp'],
            },
        }

        total_amount = 0.0
        total_retention = 0.0
        for values in values_per_grouping_key.values():
            if values['grouping_key'] and values['grouping_key']['l10n_es_type'] == 'retencion':
                total_retention += values['tax_amount']
            else:
                total_amount += values['tax_amount']

        # Aggregate the base lines again (with no grouping) to add the base amount to the total.
        def totals_grouping_function(base_line, tax_data):
            return True if tax_data else None

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, totals_grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)

        for values in values_per_grouping_key.values():
            total_amount += values['base_amount']

        if is_refund:
            total_amount = -total_amount
            total_retention = -total_retention

        return {
            'invoice_info': invoice_info,
            'total_amount': total_amount,
            'total_retention': total_retention,
        }

    @api.model
    def _get_importe_desglose_foreign_partner(self, base_lines, is_refund):
        AccountTax = self.env['account.tax']

        def tax_details_info_grouping_function(base_line, tax_data):
            if not tax_data:
                return None
            tax = tax_data['tax']

            return {
                'applied_tax_amount': tax.amount,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_exempt_reason': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'is_reverse_charge': tax_data['is_reverse_charge'],
                'tax_scope': tax.tax_scope,
                'is_refund': base_line['is_refund'],
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, tax_details_info_grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)

        invoice_info = {}
        for scope, target_key in (('service', 'PrestacionServicios'), ('consu', 'Entrega')):
            service_values_list = [
                values
                for values in values_per_grouping_key.values()
                if values['grouping_key'] and values['grouping_key']['tax_scope'] == scope
            ]
            if service_values_list:
                tax_details_info = self._build_tax_details_info(service_values_list)
                invoice_info.setdefault('DesgloseTipoOperacion', {})[target_key] = {
                    **tax_details_info['sujeta_no_sujeta'],
                    'S1': tax_details_info['sujeto'],
                    'S2': tax_details_info['sujeto_isp'],
                }

        total_amount = 0.0
        total_retention = 0.0
        for values in values_per_grouping_key.values():
            if values['grouping_key'] and values['grouping_key']['l10n_es_type'] == 'retencion':
                total_retention += values['tax_amount']
            else:
                total_amount += values['tax_amount']

        # Aggregate the base lines again (with no grouping) to add the base amount to the total.
        def totals_grouping_function(base_line, tax_data):
            return True if tax_data else None

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, totals_grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)

        for values in values_per_grouping_key.values():
            total_amount += values['base_amount']

        if is_refund:
            total_amount = -total_amount
            total_retention = -total_retention

        return {
            'invoice_info': invoice_info,
            'total_amount': total_amount,
            'total_retention': total_retention,
        }

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
            'epigrafe': self.env['ir.config_parameter'].sudo().get_param('l10n_es_edi_tbai.epigrafe', ''),
            'batuz_correction': self.env.context.get('batuz_correction'),
        }
        lroe_values.update(values)
        lroe_str = self.env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main_recibidas', lroe_values)
        lroe_xml = cleanup_xml_node(lroe_str)

        return lroe_xml

    # -------------------------------------------------------------------------
    # SIGNATURE AND QR CODE
    # -------------------------------------------------------------------------

    @api.model
    def _get_tbai_sequence_and_number_purchase(self):
        ''' Get the numbers in the case of vendor bills of Bizkaia'''
        self.ensure_one()
        original_vendor_bill = self.env['account.move'].search([('l10n_es_tbai_post_document_id', '=', self.id)],
                                                               limit=1)
        if original_vendor_bill and self.is_cancel: # Normally it should be is_cancel in this case
            vals = original_vendor_bill.l10n_es_tbai_post_document_id._get_values_from_xml({
                'sequence': './/CabeceraFactura/SerieFactura',
                'number': './/CabeceraFactura/NumFactura',
            })
            if vals['sequence'] and vals['number']:
                return vals['sequence'], vals['number']

        sequence = "TEST" if self.company_id.l10n_es_tbai_test_env else ""
        return sequence, self.name

    @api.model
    def _get_tbai_seq_from_name(self, name):
        matching = list(re.finditer(r'\d+', name))[-1]
        sequence_prefix = name[:matching.start()]
        sequence_number = int(matching.group())

        # NOTE non-decimal characters should not appear in the number
        seq_length = self.env['sequence.mixin']._get_sequence_format_param(name)[1]['seq_length']
        number = f"{sequence_number:0{seq_length}d}"

        sequence = sequence_prefix.rstrip('/')
        sequence = re.sub(r"[^0-9A-Za-z.\_\-\/]+", "", sequence)  # remove forbidden characters
        sequence = re.sub(r"\s+", " ", sequence)  # no more than one consecutive whitespace allowed
        # NOTE (optional) not recommended to use chars out of ([0123456789ABCDEFGHJKLMNPQRSTUVXYZ.\_\-\/ ])
        sequence += "TEST" if self.company_id.l10n_es_tbai_test_env else ""
        return sequence[-20:], number

    def _get_tbai_sequence_and_number(self):
        """Get the TicketBAI sequence a number values for this invoice."""
        self.ensure_one()
        return self._get_tbai_seq_from_name(self.name)

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
