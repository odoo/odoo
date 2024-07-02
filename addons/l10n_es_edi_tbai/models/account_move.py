# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gzip
import json
from base64 import b64decode, b64encode
from collections import defaultdict
from datetime import datetime
from re import sub as regex_sub
from uuid import uuid4

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID
from lxml import etree
from markupsafe import Markup, escape
from pytz import timezone
from requests.exceptions import RequestException

from odoo import _, api, fields, models, release
from odoo.addons.l10n_es_edi_sii.models.account_edi_format import PatchedHTTPAdapter
from odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_agencies import get_key
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import (
    NS_MAP, bytes_as_block, calculate_references_digests,
    cleanup_xml_signature, fill_signature, int_as_bytes)
from odoo.exceptions import UserError
from odoo.tools import get_lang
from odoo.tools.float_utils import float_repr, float_round
from odoo.tools.xml_utils import cleanup_xml_node, validate_xml_from_attachment

L10N_ES_TBAI_CRC8_TABLE = [
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

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Stored fields
    l10n_es_tbai_chain_index = fields.Integer(
        string="TicketBAI chain index",
        help="Invoice index in chain, set if and only if an in-chain XML was submitted and did not error",
        copy=False, readonly=True,
    )
    l10n_es_tbai_state = fields.Selection([
            ('to_send', 'To Send'),
            ('sent', 'Sent'),
            ('cancelled', 'Cancelled'),
        ],
        string='TicketBAI status',
        default='to_send',
        copy=False,
    )

    # Attachment fields
    l10n_es_tbai_post_file = fields.Binary(
        string='TicketBAI Post File',
        attachment=True,
        copy=False,
    )
    l10n_es_tbai_post_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='TicketBAI Post Attachment',
        compute=lambda self: self._compute_linked_attachment_id('l10n_es_tbai_post_attachment_id', 'l10n_es_tbai_post_file'),
        depends=['l10n_es_tbai_post_file'],
    )
    l10n_es_tbai_cancel_file = fields.Binary(
        string='TicketBAI Cancel File',
        attachment=True,
        copy=False,
    )
    l10n_es_tbai_cancel_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='TicketBAI Cancel Attachment',
        compute=lambda self: self._compute_linked_attachment_id('l10n_es_tbai_cancel_attachment_id', 'l10n_es_tbai_cancel_file'),
        depends=['l10n_es_tbai_cancel_file'],
    )

    # Non-stored fields
    l10n_es_tbai_is_required = fields.Boolean(
        string="TicketBAI required",
        help="Is the Basque EDI (TicketBAI) needed ?",
        compute="_compute_l10n_es_tbai_is_required",
    )

    # Optional fields
    l10n_es_tbai_refund_reason = fields.Selection(
        selection=[
            ('R1', "R1: Art. 80.1, 80.2, 80.6 and rights founded error"),
            ('R2', "R2: Art. 80.3"),
            ('R3', "R3: Art. 80.4"),
            ('R4', "R4: Art. 80 - other"),
            ('R5', "R5: Factura rectificativa en facturas simplificadas"),
        ],
        string="Invoice Refund Reason Code (TicketBai)",
        help="BOE-A-1992-28740. Ley 37/1992, de 28 de diciembre, del Impuesto sobre el "
        "Valor Añadido. Artículo 80. Modificación de la base imponible.",
        copy=False,
    )
    l10n_es_tbai_reversed_ids = fields.Many2many(
        'account.move', 'account_move_tbai_reversed_moves', 'refund_id', 'reversed_move_id',
        string="Refunded Vendor Bills",
        domain="[('move_type', '=', 'in_invoice'), ('commercial_partner_id', '=', commercial_partner_id)]",
        help="In the case where a vendor refund has multiple original invoices, you can set them here. ",
    )

    # -------------------------------------------------------------------------
    # API-DECORATED & EXTENDED METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'company_id')
    def _compute_l10n_es_tbai_is_required(self):
        for move in self:
            move.l10n_es_tbai_is_required = (move.is_sale_document() or move.is_purchase_document() and move.company_id.l10n_es_tbai_tax_agency == 'bizkaia'
                                             and not any(t.l10n_es_type == 'ignore' for t in move.invoice_line_ids.tax_ids))\
                and move.country_code == 'ES' \
                and move.company_id.l10n_es_tbai_tax_agency

    @api.depends('state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS account_edi account.move
        super()._compute_show_reset_to_draft_button()

        for move in self:
            if move.l10n_es_tbai_chain_index:
                move.show_reset_to_draft_button = False

    def button_draft(self):
        # EXTENDS account account.move
        for move in self:
            if move.l10n_es_tbai_chain_index and move.l10n_es_tbai_state != 'cancelled':
                # NOTE this last condition (state is cancelled) is there because
                # button_cancel calls button_draft.
                # Draft button does not appear for user.
                raise UserError(_("You cannot reset to draft an entry that has been posted to TicketBAI's chain"))
        super().button_draft()

    @api.ondelete(at_uninstall=False)
    def _l10n_es_tbai_unlink_except_in_chain(self):
        # Prevent deleting moves that are part of the TicketBAI chain
        if not self._context.get('force_delete') and any(m.l10n_es_tbai_chain_index for m in self):
            raise UserError(_('You cannot delete a move that has a TicketBAI chain id.'))

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_l10n_es_tbai_sequence_and_number(self):
        """Get the TicketBAI sequence a number values for this invoice."""
        self.ensure_one()
        sequence, number = self.name.rsplit('/', 1)  # NOTE non-decimal characters should not appear in the number
        sequence = regex_sub(r"[^0-9A-Za-z.\_\-\/]", "", sequence)  # remove forbidden characters
        sequence = regex_sub(r"\s+", " ", sequence)  # no more than one consecutive whitespace allowed
        # NOTE (optional) not recommended to use chars out of ([0123456789ABCDEFGHJKLMNPQRSTUVXYZ.\_\-\/ ])
        sequence += "TEST" if self.company_id.l10n_es_edi_test_env else ""
        return sequence, number

    def _get_l10n_es_tbai_signature_and_date(self):
        """
        Get the TicketBAI signature and registration date for this invoice.
        Values are read directly from the 'post' XMLs submitted to the government \
            (the 'cancel' XML is ignored).
        The registration date is the date the invoice was registered into the govt's TicketBAI servers.
        """
        self.ensure_one()
        vals = self._get_l10n_es_tbai_values_from_xml({
            'signature': r'.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue',
            'registration_date': r'.//CabeceraFactura//FechaExpedicionFactura'
        })
        # RFC2045 - Base64 Content-Transfer-Encoding (page 25)
        # Any characters outside of the base64 alphabet are to be ignored in base64-encoded data.
        signature = vals['signature'].replace("\n", "")
        registration_date = datetime.strptime(vals['registration_date'], '%d-%m-%Y')
        return signature, registration_date

    def _get_l10n_es_tbai_id(self):
        """Get the TicketBAI ID (TBAID) as defined in the TicketBAI doc."""
        self.ensure_one()
        if not self.l10n_es_tbai_chain_index:
            return ''

        signature, registration_date = self._get_l10n_es_tbai_signature_and_date()
        company = self.company_id
        tbai_id_no_crc = '-'.join([
            'TBAI',
            str(company.vat[2:] if company.vat.startswith('ES') else company.vat),
            datetime.strftime(registration_date, '%d%m%y'),
            signature[:13],
            ''  # CRC
        ])
        return tbai_id_no_crc + self._l10n_es_edi_tbai_crc8(tbai_id_no_crc)

    def _get_l10n_es_tbai_qr(self):
        """Returns the URL for the invoice's QR code.  We can not use url_encode because it escapes / e.g."""
        self.ensure_one()
        if not self.l10n_es_tbai_chain_index:
            return ''

        company = self.company_id
        sequence, number = self._get_l10n_es_tbai_sequence_and_number()
        tbai_qr_no_crc = get_key(company.l10n_es_tbai_tax_agency, 'qr_url_', company.l10n_es_edi_test_env) + '?' + '&'.join([
            'id=' + self._get_l10n_es_tbai_id(),
            's=' + sequence,
            'nf=' + number,
            'i=' + self._get_l10n_es_tbai_values_from_xml({'importe': r'.//ImporteTotalFactura'})['importe']
        ])
        qr_url = tbai_qr_no_crc + '&cr=' + self._l10n_es_edi_tbai_crc8(tbai_qr_no_crc)
        return qr_url

    def _l10n_es_edi_tbai_crc8(self, data):
        crc = 0x0
        for c in data:
            crc = L10N_ES_TBAI_CRC8_TABLE[(crc ^ ord(c)) & 0xFF]
        return '{:03d}'.format(crc & 0xFF)

    def _get_l10n_es_tbai_values_from_xml(self, xpaths):
        """
        This function reads values directly from the 'post' XML submitted to the government \
            (the 'cancel' XML is ignored).
        """
        res = dict.fromkeys(xpaths, '')
        doc_xml = self._get_l10n_es_tbai_submitted_xml()
        if doc_xml is None:
            return res
        for key, value in xpaths.items():
            res[key] = doc_xml.find(value).text
        return res

    def _get_l10n_es_tbai_submitted_xml(self, cancel=False):
        """Returns the XML object representing the post or cancel document."""
        self.ensure_one()
        self = self.with_context(bin_size=False)
        doc = self.l10n_es_tbai_cancel_file if cancel else self.l10n_es_tbai_post_file
        if not doc:
            return None
        return etree.fromstring(b64decode(doc))

    def _l10n_es_tbai_get_document_name(self, cancel=False):
        return self. name + ('_post.xml' if not cancel else '_cancel.xml')

    def _l10n_es_tbai_create_document(self, xml, cancel=False):
        res_field = 'l10n_es_tbai_post_file' if not cancel else 'l10n_es_tbai_cancel_file'
        attachment_field = 'l10n_es_tbai_post_attachment_id' if not cancel else 'l10n_es_tbai_cancel_attachment_id'
        self.env['ir.attachment'].create({
            'name': self._l10n_es_tbai_get_document_name(cancel),
            'raw': etree.tostring(xml, encoding='UTF-8'),
            'type': 'binary',
            'res_model': 'account.move',
            'res_id': self.id,
            'res_field': res_field,
        })
        self.invalidate_recordset(fnames=[res_field, attachment_field])

    def _l10n_es_tbai_post_document_in_chatter(self, message, cancel=False):
        test_suffix = '(test mode)' if self.company_id.l10n_es_edi_test_env else ''
        self.with_context(no_new_invoice=True).message_post(
            body=Markup("<pre>TicketBAI: posted {document_type} XML {test_suffix}\n{message}</pre>").format(
                document_type='emission' if not cancel else 'cancellation',
                test_suffix=test_suffix,
                message=message,
            ),
            attachment_ids=[self.l10n_es_tbai_post_attachment_id.id] if not cancel else [self.l10n_es_tbai_cancel_attachment_id.id],
        )

    # -------------------------------------------------------------------------
    # WEB SERVICE CALLS
    # -------------------------------------------------------------------------

    def l10n_es_tbai_send_bill(self):
        for bill in self:
            error = bill._l10n_es_tbai_post()
            if error:
                raise UserError(error)

    def l10n_es_tbai_cancel(self):
        for invoice in self:
            if invoice.is_purchase_document():
                cancel_xml = False  # Batuz specific
            else:
                cancel_dict = invoice._get_l10n_es_tbai_invoice_xml(cancel=True)
                cancel_xml = cancel_dict['xml_file']
                self._l10n_es_tbai_create_document(cancel_xml, cancel=True)

            res = invoice._l10n_es_tbai_post_to_web_service(cancel_xml, cancel=True)

            if res.get('success'):
                invoice.l10n_es_tbai_state = 'cancelled'
                invoice.button_cancel()
                self._l10n_es_tbai_post_document_in_chatter(res['message'], cancel=True)
            else:
                raise UserError(res.get('error'))

    def _l10n_es_tbai_post(self):
        self.ensure_one()

        # Ensure a certificate is available.
        if not self.company_id.l10n_es_edi_certificate_id:
            return _("Please configure the certificate for TicketBAI/SII.")

        # Ensure a tax agency is available.
        if not self.company_id.mapped('l10n_es_tbai_tax_agency')[0]:
            return _("Please specify a tax agency on your company for TicketBAI.")

        # Ensure a vat is available.
        if not self.company_id.vat:
            return _("Please configure the Tax ID on your company for TicketBAI.")

        # Check the refund reason
        if self.move_type == 'out_refund':
            if not self.l10n_es_tbai_refund_reason:
                return _('Refund reason must be specified (TicketBAI)')
            if self.l10n_es_is_simplified:
                if self.l10n_es_tbai_refund_reason != 'R5':
                    return _('Refund reason must be R5 for simplified invoices (TicketBAI)')
            else:
                if self.l10n_es_tbai_refund_reason == 'R5':
                    return _('Refund reason cannot be R5 for non-simplified invoices (TicketBAI)')

        if self.is_purchase_document():
            inv_xml = False  # For Ticketbai Batuz vendor bills, we get the values later as it does not need chaining, ...

        else:
            # Chain integrity check: chain head must have been REALLY posted (not timeout'ed)
            # - If called from a cron, then the re-ordering of jobs should prevent this from triggering
            # - If called manually, then the user will see this error pop up when it triggers
            chain_head = self.company_id._get_l10n_es_tbai_last_posted_invoice()
            if chain_head and chain_head != self and not chain_head.l10n_es_tbai_chain_index:
                return _("TicketBAI: Cannot post invoice while chain head (%s) has not been posted", chain_head.name)
            if self.move_type == 'out_refund' and not self.reversed_entry_id.l10n_es_tbai_chain_index:
                return _("TicketBAI: Cannot post a reversal move while the source document (%s) has not been posted", self.reversed_entry_id.name)

            # Tax configuration check: In case of foreign customer we need the tax scope to be set
            com_partner = self.commercial_partner_id
            if (com_partner.country_id.code not in ('ES', False) or (com_partner.vat or '').startswith("ESN")) and\
                    self.line_ids.tax_ids.filtered(lambda t: not t.tax_scope):
                return _(
                    "In case of a foreign customer, you need to configure the tax scope on taxes:\n%s",
                    "\n".join(self.line_ids.tax_ids.mapped('name'))
                )

            inv_dict = self._get_l10n_es_tbai_invoice_xml()
            if inv_dict.get('error'):
                return inv_dict['error']  # XSD validation failed, return result dict
            inv_xml = inv_dict['xml_file']

            self._l10n_es_tbai_create_document(inv_xml)

            # Assign unique 'chain index' from dedicated sequence
            if not self.l10n_es_tbai_chain_index:
                self.l10n_es_tbai_chain_index = self.company_id._get_l10n_es_tbai_next_chain_index()

        res = self._l10n_es_tbai_post_to_web_service(inv_xml)

        if res.get('success'):
            self.l10n_es_tbai_state = 'sent'
            self._l10n_es_tbai_post_document_in_chatter(res['message'])

        return res.get('error')

    def _l10n_es_tbai_post_to_web_service(self, invoice_xml, cancel=False):
        company = self.company_id

        try:
            # Call the web service, retrieve and parse response
            success, message, response_xml = self._l10n_es_tbai_post_to_agency(
                self.env, company.l10n_es_tbai_tax_agency, invoice_xml, cancel)
        except (RequestException) as e:
            # In case of timeout / request exception, return warning
            return {'error': str(e)}

        if success:
            return {
                'success': True,
                'message': message,
                'response': response_xml,
            }
        else:
            return {'error': message}

        return success, message, response_xml

    def _l10n_es_tbai_post_to_agency(self, env, agency, invoice_xml, cancel=False):
        if agency in ('araba', 'gipuzkoa'):
            prepare_post_method, process_post_method = self._l10n_es_tbai_prepare_post_params_ar_gi, self._l10n_es_tbai_process_post_response_ar_gi
        elif agency == 'bizkaia':
            prepare_post_method, process_post_method = self._l10n_es_tbai_prepare_post_params_bi, self._l10n_es_tbai_process_post_response_bi
        params = prepare_post_method(env, agency, invoice_xml, cancel)
        response = self._l10n_es_tbai_send_request_to_agency(timeout=10, **params)
        return process_post_method(env, response)

    @api.model
    def _l10n_es_tbai_send_request_to_agency(self, *args, **kwargs):
        session = requests.Session()
        session.cert = kwargs.pop('pkcs12_data')
        session.mount("https://", PatchedHTTPAdapter())
        response = session.request('post', *args, **kwargs)
        response.raise_for_status()
        return response

    def _l10n_es_tbai_prepare_post_params_ar_gi(self, env, agency, invoice_xml, cancel=False):
        """Web service parameters for Araba and Gipuzkoa."""
        company = self.company_id
        return {
            'url': get_key(agency, 'cancel_url_' if cancel else 'post_url_', company.l10n_es_edi_test_env),
            'headers': {"Content-Type": "application/xml; charset=utf-8"},
            'pkcs12_data': company.l10n_es_edi_certificate_id,
            'data': etree.tostring(invoice_xml, encoding='UTF-8'),
        }

    @api.model
    def _l10n_es_tbai_process_post_response_ar_gi(self, env, response):
        """Government response processing for Araba and Gipuzkoa."""
        try:
            response_xml = etree.fromstring(response.content)
        except etree.XMLSyntaxError as e:
            return False, e, None

        # Error management
        message = ''
        already_received = False
        # Get message in basque if env is in basque
        msg_node_name = 'Azalpena' if get_lang(env).code == 'eu_ES' else 'Descripcion'
        for xml_res_node in response_xml.findall(r'.//ResultadosValidacion'):
            message_code = xml_res_node.find('Codigo').text
            message += message_code + ": " + xml_res_node.find(msg_node_name).text + "\n"
            if message_code in ('005', '019'):
                already_received = True  # error codes 5/19 mean XML was already received with that sequence
        response_code = int(response_xml.find(r'.//Estado').text)
        response_success = (response_code == 0) or already_received

        return response_success, message, response_xml

    def _get_vendor_bill_tax_values(self):
        self.ensure_one()
        results = defaultdict(lambda: {'base_amount': 0.0, 'tax_amount': 0.0})
        amount_total = 0.0
        for line in self.line_ids.filtered(lambda l: l.display_type in ('product', 'tax')):
            if any(t.l10n_es_type == 'ignore' for t in line.tax_ids) or line.tax_line_id.l10n_es_type == 'ignore':
                continue
            if line.tax_line_id.l10n_es_type != 'retencion':
                amount_total += line.balance
            for tax in line.tax_ids.filtered(lambda t: t.l10n_es_type not in ('recargo', 'retencion')):
                results[tax]['base_amount'] += line.balance

            if ((tax := line.tax_line_id) and tax.l10n_es_type not in ('recargo', 'retencion') and
                line.tax_repartition_line_id.factor_percent != -100.0):
                results[tax]['tax_amount'] += line.balance
        iva_values = []
        for tax in results:
            code = "C" # Bienes Corrientes
            if tax.l10n_es_bien_inversion:
                code = "I" # Investment Goods
            if tax.tax_scope == 'service':
                code = 'G' # Gastos
            iva_values.append({'base': results[tax]['base_amount'],
                               'code': code,
                               'tax': results[tax]['tax_amount'],
                               'rec': tax})
        return {'iva_values': iva_values,
                'amount_total': amount_total}

    def _l10n_es_tbai_get_in_invoice_values_batuz(self):
        """ For the vendor bills for Bizkaia, the structure is different than the regular Ticketbai XML (LROE)"""
        values = {
            **self._l10n_es_tbai_get_subject_values(False),
            **self._l10n_es_tbai_get_header_values(),
             **self._get_vendor_bill_tax_values(),
            'invoice': self,
            'datetime_now': datetime.now(tz=timezone('Europe/Madrid')),
            'format_date': lambda d: datetime.strftime(d, '%d-%m-%Y'),
            'format_time': lambda d: datetime.strftime(d, '%H:%M:%S'),
            'format_float': lambda f: float_repr(f, precision_digits=2),
        }
        # Check if intracom
        mod_303_10 = self.env.ref('l10n_es.mod_303_casilla_10_balance')._get_matching_tags()
        mod_303_11 = self.env.ref('l10n_es.mod_303_casilla_11_balance')._get_matching_tags()
        tax_tags = self.invoice_line_ids.tax_ids.repartition_line_ids.tag_ids
        intracom = bool(tax_tags & (mod_303_10 + mod_303_11))
        values['regime_key'] = ['09'] if intracom else ['01']
        # Credit notes (factura rectificativa)
        values['is_refund'] = self.move_type == 'in_refund'
        if values['is_refund']:
            values['credit_note_code'] = self.l10n_es_tbai_refund_reason
            values['credit_note_invoices'] = self.reversed_entry_id | self.l10n_es_tbai_reversed_ids
        values['tipofactura'] = 'F5' if self._l10n_es_is_dua() else 'F1'
        return values

    def _l10n_es_tbai_prepare_values_bi(self, invoice_xml, cancel=False):
        sender = self.company_id
        lroe_values = {
            'is_emission': not cancel,
            'sender': sender,
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'fiscal_year': str(self.date.year),
        }
        if self.is_sale_document():
            lroe_values.update({'tbai_b64_list': [b64encode(etree.tostring(invoice_xml, encoding="UTF-8")).decode()]})
        else:
            lroe_values.update(self._l10n_es_tbai_get_in_invoice_values_batuz())
        return lroe_values

    def _l10n_es_tbai_prepare_post_params_bi(self, env, agency, invoice_xml, cancel=False):
        """Web service parameters for Bizkaia."""
        lroe_values = self._l10n_es_tbai_prepare_values_bi(invoice_xml, cancel=cancel)
        if self.is_purchase_document():
            lroe_str = env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main_recibidas', lroe_values)
            lroe_xml = cleanup_xml_node(lroe_str)
            if lroe_xml is not None:
                self._l10n_es_tbai_create_document(lroe_xml, cancel)
        else:
            lroe_str = env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main', lroe_values)

        lroe_xml = cleanup_xml_node(lroe_str)
        lroe_str = etree.tostring(lroe_xml, encoding="UTF-8")
        lroe_bytes = gzip.compress(lroe_str)

        company = self.company_id
        return {
            'url': get_key(agency, 'cancel_url_' if cancel else 'post_url_', company.l10n_es_edi_test_env),
            'headers': {
                'Accept-Encoding': 'gzip',
                'Content-Encoding': 'gzip',
                'Content-Length': str(len(lroe_str)),
                'Content-Type': 'application/octet-stream',
                'eus-bizkaia-n3-version': '1.0',
                'eus-bizkaia-n3-content-type': 'application/xml',
                'eus-bizkaia-n3-data': json.dumps({
                    'con': 'LROE',
                    'apa': '1.1' if self.is_sale_document() else '2',
                    'inte': {
                        'nif': lroe_values['sender_vat'],
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
            'pkcs12_data': self.company_id.l10n_es_edi_certificate_id,
            'data': lroe_bytes,
        }

    @api.model
    def _l10n_es_tbai_process_post_response_bi(self, env, response):
        """Government response processing for Bizkaia."""
        # GLOBAL STATUS (LROE)
        response_messages = []
        response_success = True
        if response.headers['eus-bizkaia-n3-tipo-respuesta'] != "Correcto":
            code = response.headers['eus-bizkaia-n3-codigo-respuesta']
            response_messages.append(code + ': ' + response.headers['eus-bizkaia-n3-mensaje-respuesta'])
            response_success = False

        response_data = response.content
        response_xml = None
        if response_data:
            try:
                response_xml = etree.fromstring(response_data)
            except etree.XMLSyntaxError as e:
                response_success = False
                response_messages.append(str(e))
        else:
            response_success = False
            response_messages.append(_('No XML response received from LROE.'))

        # INVOICE STATUS (only one in batch)
        # Get message in basque if env is in basque
        if response_xml is not None:
            msg_node_name = 'DescripcionErrorRegistro' + ('EU' if get_lang(env).code == 'eu_ES' else 'ES')
            invoice_success = response_xml.find(r'.//EstadoRegistro').text == "Correcto"
            if not invoice_success:
                invoice_code = response_xml.find(r'.//CodigoErrorRegistro').text
                if invoice_code == "B4_2000003":  # already received
                    invoice_success = True
                response_messages.append(invoice_code + ": " + (response_xml.find(rf'.//{msg_node_name}').text or ''))

        return response_success and invoice_success, '<br/>'.join(response_messages), response_xml

    # -------------------------------------------------------------------------
    # XML DOCUMENT
    # -------------------------------------------------------------------------

    L10N_ES_TBAI_VERSION = 1.2

    def _get_l10n_es_tbai_invoice_xml(self, cancel=False):
        self.ensure_one()

        def format_float(value, precision_digits=2):
            rounded_value = float_round(value, precision_digits=precision_digits)
            return float_repr(rounded_value, precision_digits=precision_digits)

        # Otherwise, generate a new XML
        values = {
            **self.company_id._get_l10n_es_tbai_license_dict(),
            **self._l10n_es_tbai_get_header_values(),
            **self._l10n_es_tbai_get_subject_values(cancel),
            **self._l10n_es_tbai_get_invoice_values(cancel),
            **self._l10n_es_tbai_get_trail_values(cancel),
            'is_emission': not cancel,
            'datetime_now': datetime.now(tz=timezone('Europe/Madrid')),
            'format_date': lambda d: datetime.strftime(d, '%d-%m-%Y'),
            'format_time': lambda d: datetime.strftime(d, '%H:%M:%S'),
            'format_float': format_float,
        }
        template_name = 'l10n_es_edi_tbai.template_invoice_main' + ('_cancel' if cancel else '_post')
        xml_str = self.env['ir.qweb']._render(template_name, values)
        xml_doc = cleanup_xml_node(xml_str, remove_blank_nodes=False)
        try:
            xml_doc = self._l10n_es_tbai_sign_invoice(xml_doc)
        except ValueError:
            raise UserError(_('No valid certificate found for this company, TicketBAI file will not be signed.\n'))
        res = {'xml_file': xml_doc}

        # Optional check using the XSD
        res.update(self._l10n_es_tbai_validate_xml_with_xsd(xml_doc, cancel, self.company_id.l10n_es_tbai_tax_agency))
        return res

    @api.model
    def _l10n_es_tbai_get_header_values(self):
        return {
            'tbai_version': self.L10N_ES_TBAI_VERSION,
            'odoo_version': release.version,
        }

    def _l10n_es_tbai_get_subject_values(self, cancel):
        # === SENDER (EMISOR) ===
        sender = self.company_id
        values = {
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'sender': sender,
        }
        if cancel:
            return values  # cancellation invoices do not specify recipients (they stay the same)

        # NOTE: TicketBai supports simplified invoices WITH recipients but we don't for now (we should for POS)
        # NOTE: TicketBAI credit notes for simplified invoices are ALWAYS simplified BUT can have a recipient even if invoice doesn't
        if self.l10n_es_is_simplified:
            return values  # do not set 'recipient' unless there is an actual recipient (used as condition in template)

        # === RECIPIENTS (DESTINATARIOS) ===
        nif = False
        alt_id_country = False
        partner = self.commercial_partner_id
        alt_id_number = partner.vat or 'NO_DISPONIBLE'
        alt_id_type = ""
        if (not partner.country_id or partner.country_id.code == 'ES') and partner.vat:
            # ES partner with VAT.
            nif = partner.vat[2:] if partner.vat.startswith('ES') else partner.vat
        elif partner.country_id.code in self.env.ref('base.europe').country_ids.mapped('code'):
            # European partner
            alt_id_type = '02'
        else:
            # Non-european partner
            if partner.vat:
                alt_id_type = '04'
            else:
                alt_id_type = '06'
            if partner.country_id:
                alt_id_country = partner.country_id.code

        values_dest = {
            'nif': nif,
            'alt_id_country': alt_id_country,
            'alt_id_number': alt_id_number,
            'alt_id_type': alt_id_type,
            'partner': partner,
            'partner_address': ', '.join(filter(None, [partner.street, partner.street2, partner.city])),
        }

        values.update({
            'recipient': values_dest,
        })
        return values

    def _l10n_es_tbai_get_invoice_values(self, cancel):
        # Header
        values = {'invoice': self}
        if cancel:
            return values

        # Credit notes (factura rectificativa)
        # NOTE values below would have to be adapted for purchase invoices (Bizkaia LROE)
        values['is_refund'] = self.move_type == 'out_refund'
        if values['is_refund']:
            values['credit_note_code'] = self.l10n_es_tbai_refund_reason
            values['credit_note_invoice'] = self.reversed_entry_id

        # Lines (detalle)
        refund_sign = (1 if values['is_refund'] else -1)
        invoice_lines = []
        for line in self.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
            if line.discount == 100.0:
                inverse_currency_rate = abs(line.move_id.amount_total_signed / line.move_id.amount_total) if line.move_id.amount_total else 1
                balance_before_discount = - line.price_unit * line.quantity * inverse_currency_rate
            else:
                balance_before_discount = line.balance / (1 - line.discount / 100)
            discount = (balance_before_discount - line.balance)
            line_price_total = self._l10n_es_tbai_get_invoice_line_price_total(line)

            if not any(t.l10n_es_type == 'sujeto_isp' for t in line.tax_ids):
                total = line_price_total * abs(line.balance / line.amount_currency if line.amount_currency != 0 else 1) * -refund_sign
            else:
                total = abs(line.balance) * -refund_sign * (-1 if line_price_total < 0 else 1)
            invoice_lines.append({
                'line': line,
                'discount': discount * refund_sign,
                'unit_price': (line.balance + discount) / line.quantity * refund_sign if line.quantity > 0 else 0,
                'total': total,
                'description': regex_sub(r'[^0-9a-zA-Z ]', '', line.product_id.display_name or line.name or '')[:250]
            })
        values['invoice_lines'] = invoice_lines
        # Tax details (desglose)
        importe_total, desglose, amount_retention = self._l10n_es_tbai_get_importe_desglose()
        values['amount_total'] = importe_total
        values['invoice_info'] = desglose
        values['amount_retention'] = amount_retention * refund_sign if amount_retention != 0.0 else 0.0

        # Regime codes (ClaveRegimenEspecialOTrascendencia)
        # NOTE there's 11 more codes to implement, also there can be up to 3 in total
        # See https://www.gipuzkoa.eus/documents/2456431/13761128/Anexo+I.pdf/2ab0116c-25b4-f16a-440e-c299952d683d
        export_exempts = self.invoice_line_ids.tax_ids.filtered(lambda t: t.l10n_es_exempt_reason == 'E2')
        values['regime_key'] = ['02'] if export_exempts else ['01']

        if self.l10n_es_is_simplified and self.company_id.l10n_es_tbai_tax_agency != 'bizkaia':
            values['regime_key'] += ['52']  # code for simplified invoices

        return values

    @api.model
    def _l10n_es_tbai_get_invoice_line_price_total(self, invoice_line):
        price_total = invoice_line.price_total
        retention_tax_lines = invoice_line.tax_ids.filtered(lambda t: t.l10n_es_type == "retencion")
        if retention_tax_lines:
            line_discount_price_unit = invoice_line.price_unit * (1 - (invoice_line.discount / 100.0))
            tax_lines_no_retention = invoice_line.tax_ids - retention_tax_lines
            if tax_lines_no_retention:
                taxes_res = tax_lines_no_retention.compute_all(line_discount_price_unit,
                                                               quantity=invoice_line.quantity,
                                                               currency=invoice_line.currency_id,
                                                               product=invoice_line.product_id,
                                                               partner=invoice_line.move_id.partner_id,
                                                               is_refund=invoice_line.is_refund)
                price_total = taxes_res['total_included']
        return price_total

    def _l10n_es_tbai_get_importe_desglose(self):
        com_partner = self.commercial_partner_id
        sign = -1 if self.move_type in ('out_refund', 'in_refund') else 1
        if com_partner.country_id.code in ('ES', False) and not (com_partner.vat or '').startswith("ESN"):
            tax_details_info_vals = self._l10n_es_edi_get_invoices_tax_details_info()
            tax_amount_retention = tax_details_info_vals['tax_amount_retention']
            desglose = {'DesgloseFactura': tax_details_info_vals['tax_details_info']}
            desglose['DesgloseFactura'].update({'S1': tax_details_info_vals['S1_list'],
                                                'S2': tax_details_info_vals['S2_list']})
            importe_total = round(sign * (
                tax_details_info_vals['tax_details']['base_amount']
                + tax_details_info_vals['tax_details']['tax_amount']
                - tax_amount_retention
            ), 2)
        else:
            tax_details_info_service_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                filter_invl_to_apply=lambda x: any(t.tax_scope == 'service' for t in x.tax_ids)
            )
            tax_details_info_consu_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                filter_invl_to_apply=lambda x: any(t.tax_scope == 'consu' for t in x.tax_ids)
            )
            service_retention = tax_details_info_service_vals['tax_amount_retention']
            consu_retention = tax_details_info_consu_vals['tax_amount_retention']
            desglose = {}
            if tax_details_info_service_vals['tax_details_info']:
                desglose.setdefault('DesgloseTipoOperacion', {})
                desglose['DesgloseTipoOperacion']['PrestacionServicios'] = tax_details_info_service_vals['tax_details_info']
                desglose['DesgloseTipoOperacion']['PrestacionServicios'].update(
                    {'S1': tax_details_info_service_vals['S1_list'],
                     'S2': tax_details_info_service_vals['S2_list']})

            if tax_details_info_consu_vals['tax_details_info']:
                desglose.setdefault('DesgloseTipoOperacion', {})
                desglose['DesgloseTipoOperacion']['Entrega'] = tax_details_info_consu_vals['tax_details_info']
                desglose['DesgloseTipoOperacion']['Entrega'].update(
                    {'S1': tax_details_info_consu_vals['S1_list'],
                     'S2': tax_details_info_consu_vals['S2_list']})
            importe_total = round(sign * (
                tax_details_info_service_vals['tax_details']['base_amount']
                + tax_details_info_service_vals['tax_details']['tax_amount']
                - service_retention
                + tax_details_info_consu_vals['tax_details']['base_amount']
                + tax_details_info_consu_vals['tax_details']['tax_amount']
                - consu_retention
            ), 2)
            tax_amount_retention = service_retention + consu_retention
        return importe_total, desglose, tax_amount_retention

    def _l10n_es_tbai_get_trail_values(self, cancel):
        prev_invoice = self.company_id._get_l10n_es_tbai_last_posted_invoice()
        # NOTE: assumtion that last posted == previous works because XML is generated on post
        if prev_invoice and not cancel:
            return {
                'chain_prev_invoice': prev_invoice
            }
        else:
            return {}

    def _l10n_es_tbai_sign_invoice(self, xml_root):
        company = self.company_id
        cert_private, cert_public = company.l10n_es_edi_certificate_id._get_key_pair()
        public_key = cert_public.public_key()

        # Identifiers
        document_id = "Document-" + str(uuid4())
        signature_id = "Signature-" + document_id
        keyinfo_id = "KeyInfo-" + document_id
        sigproperties_id = "SignatureProperties-" + document_id

        # Render digital signature scaffold from QWeb
        common_name = cert_public.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        org_unit = cert_public.issuer.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value
        org_name = cert_public.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
        country_name = cert_public.issuer.get_attributes_for_oid(NameOID.COUNTRY_NAME)[0].value
        values = {
            'dsig': {
                'document_id': document_id,
                'x509_certificate': bytes_as_block(cert_public.public_bytes(encoding=serialization.Encoding.DER)),
                'public_modulus': bytes_as_block(int_as_bytes(public_key.public_numbers().n)),
                'public_exponent': bytes_as_block(int_as_bytes(public_key.public_numbers().e)),
                'iso_now': datetime.now().isoformat(),
                'keyinfo_id': keyinfo_id,
                'signature_id': signature_id,
                'sigproperties_id': sigproperties_id,
                'reference_uri': "Reference-" + document_id,
                'sigpolicy_url': get_key(company.l10n_es_tbai_tax_agency, 'sigpolicy_url'),
                'sigpolicy_digest': get_key(company.l10n_es_tbai_tax_agency, 'sigpolicy_digest'),
                'sigcertif_digest': b64encode(cert_public.fingerprint(hashes.SHA256())).decode(),
                'x509_issuer_description': f'CN={common_name}, OU={org_unit}, O={org_name}, C={country_name}',
                'x509_serial_number': cert_public.serial_number,
            }
        }
        xml_sig_str = self.env['ir.qweb']._render('l10n_es_edi_tbai.template_digital_signature', values)
        xml_sig = cleanup_xml_signature(xml_sig_str)

        # Complete document with signature template
        xml_root.append(xml_sig)

        # Compute digest values for references
        calculate_references_digests(xml_sig.find("SignedInfo", namespaces=NS_MAP))

        # Sign (writes into SignatureValue)
        fill_signature(xml_sig, cert_private)

        return xml_root

    @api.model
    def _l10n_es_tbai_validate_xml_with_xsd(self, xml_doc, cancel, tax_agency):
        xsd_name = get_key(tax_agency, 'xsd_name')['cancel' if cancel else 'post']
        try:
            validate_xml_from_attachment(self.env, xml_doc, xsd_name, prefix='l10n_es_edi_tbai')
        except UserError as e:
            return {'error': escape(str(e)), 'blocking_level': 'error'}
        return {}
