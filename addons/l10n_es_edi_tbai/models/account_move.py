# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from re import sub as regex_sub

from lxml import etree
from odoo import api, fields, models
from pytz import timezone
from werkzeug.urls import url_quote


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Stored fields
    l10n_es_tbai_is_required = fields.Boolean(
        string="Is the Bask EDI (TicketBAI) needed",
        compute='_compute_l10n_es_tbai_is_required'
    )

    # Relations
    l10n_es_tbai_temp_xml = fields.Many2one(
        comodel_name='ir.attachment', readonly=True,
        string="Temp XML (awaiting response)",
        help="Stores the posted XML while no answer has been received from the govt (avoids loss of info in case of timeouts)."
    )

    # Non-stored fields
    l10n_es_tbai_sequence = fields.Char(string="TicketBAI sequence", compute="_compute_l10n_es_tbai_sequence")
    l10n_es_tbai_number = fields.Char(string="TicketBAI number", compute="_compute_l10n_es_tbai_number")
    l10n_es_tbai_id = fields.Char(string="TicketBAI ID", compute="_compute_l10n_es_tbai_id")
    l10n_es_tbai_signature = fields.Char(string="Signature value of XML", compute="_compute_l10n_es_tbai_values")
    l10n_es_tbai_registration_date = fields.Date(  # TODO replace with record.invoice_date ?
        string="Registration Date",
        help="Technical field to keep the date the invoice was sent the first time as the date the invoice was "
             "registered into the system.",
        compute="_compute_l10n_es_tbai_values"
    )
    l10n_es_tbai_qr = fields.Char(string="QR code to verify posted invoice", compute="_compute_l10n_es_tbai_qr")
    l10n_es_tbai_qr_escaped = fields.Char(string="QR code, escaped", compute="_compute_l10n_es_tbai_qr_escaped")

    # Optional fields
    l10n_es_tbai_refund_reason = fields.Selection([
        ('R1', "R1: Art. 80.1, 80.2, 80.6 and rights founded error"),
        ('R2', "R2: Art. 80.3"),
        ('R3', "R3: Art. 80.4"),
        ('R4', "R4: Art. 80 - other"),
        ('R5', "R5: Factura rectificativa en facturas simplificadas")
    ],
        string="Invoice Refund Reason Code",
        help="BOE-A-1992-28740. Ley 37/1992, de 28 de diciembre, del Impuesto sobre el "
        "Valor Añadido. Artículo 80. Modificación de la base imponible.",
        copy=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'company_id')
    def _compute_l10n_es_tbai_is_required(self):
        for move in self:
            move.l10n_es_tbai_is_required = move.is_sale_document() \
                and move.country_code == 'ES' \
                and move.company_id.l10n_es_tbai_tax_agency

    @api.depends('company_id', 'state')
    def _compute_l10n_es_tbai_id(self):
        for record in self:
            if record.l10n_es_tbai_is_required:
                # TODO (POS): pre-sign document and store it as EDI document (before posting), only then get signature
                # rationale: signature changes every time doc is signed, but needs to be consistent across XMLs / TBAI IDs
                if record.l10n_es_tbai_signature == '':
                    record.l10n_es_tbai_id = ''
                else:
                    company = record.company_id
                    tbai_id_no_crc = '-'.join([
                        'TBAI',
                        str(company.vat[2:] if company.vat.startswith('ES') else company.vat),
                        datetime.strftime(record.l10n_es_tbai_registration_date, '%d%m%y'),  # TODO use record.invoice_date ? (also in XMLs)
                        record.l10n_es_tbai_signature[:13],
                        ''  # CRC
                    ])
                    record.l10n_es_tbai_id = tbai_id_no_crc + self.env['l10n_es.edi.tbai.util']._crc8(tbai_id_no_crc)
            else:
                record.l10n_es_tbai_id = ''  # record

    @api.depends('l10n_es_tbai_id')
    def _compute_l10n_es_tbai_qr(self):
        for record in self:
            if record.l10n_es_tbai_is_required and record.edi_state != 'to_send':
                company = record.company_id
                tbai_qr_no_crc = company.get_l10n_es_tbai_url_qr() + '?' + '&'.join([
                    'id=' + record.l10n_es_tbai_id,
                    's=' + record.l10n_es_tbai_sequence,
                    'nf=' + record.l10n_es_tbai_number,
                    'i=' + record._get_l10n_es_tbai_values_from_xml({'importe': r'.//ImporteTotalFactura'})['importe']
                ])
                record.l10n_es_tbai_qr = tbai_qr_no_crc + '&cr=' + self.env['l10n_es.edi.tbai.util']._crc8(tbai_qr_no_crc)
            else:
                record.l10n_es_tbai_qr = ''

    @api.depends('l10n_es_tbai_qr')
    def _compute_l10n_es_tbai_qr_escaped(self):
        for record in self:
            record.l10n_es_tbai_qr_escaped = url_quote(record.l10n_es_tbai_qr)

    def _get_l10n_es_tbai_values_from_xml(self, xpaths):
        res = {key: '' for key in xpaths.keys()}
        for doc in self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id)
        ]):
            doc_xml = etree.fromstring(doc.with_context(bin_size=False).raw)  # Without bin_size=False, size is returned instead of content
            for key, value in xpaths.items():
                res[key] = doc_xml.find(value).text
            return res
        return res

    @api.depends('edi_document_ids.attachment_id.raw')
    def _compute_l10n_es_tbai_values(self):
        for record in self:
            vals = record._get_l10n_es_tbai_values_from_xml({
                'signature': r'.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue',
                'registration_date': r'.//CabeceraFactura//FechaExpedicionFactura'
            })
            record.l10n_es_tbai_signature = vals['signature']
            if vals['registration_date']:
                record.l10n_es_tbai_registration_date = datetime.strptime(vals['registration_date'], '%d-%m-%Y').replace(tzinfo=timezone('Europe/Madrid'))
            else:
                record.l10n_es_tbai_registration_date = None

    @api.depends('name')
    def _compute_l10n_es_tbai_sequence(self):
        for record in self:
            sequence, _ = record.name.rsplit('/', 1)
            sequence = regex_sub(r"[^0-9A-Za-z.\_\-\/]", "", sequence)  # remove forbidden characters
            sequence = regex_sub(r"[\s]+", " ", sequence)  # no more than once consecutive whitespace allowed
            # TODO (optional) issue warning if sequence uses chars out of ([0123456789ABCDEFGHJKLMNPQRSTUVXYZ.\_\-\/ ])
            self.l10n_es_tbai_sequence = sequence + ("TEST" if record.company_id.l10n_es_tbai_test_env else "")

    @ api.depends('name')
    def _compute_l10n_es_tbai_number(self):
        for record in self:
            _, number = record.name.rsplit('/', 1)
            self.l10n_es_tbai_number = regex_sub(r"[^0-9]", "", number)  # remove non-decimal characters
