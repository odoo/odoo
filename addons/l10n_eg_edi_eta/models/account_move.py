# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import json

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero
from odoo.tools.sql import column_exists, create_column
from datetime import datetime

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_eg_long_id = fields.Char(string='ETA Long ID', compute='_compute_eta_long_id')
    l10n_eg_qr_code = fields.Char(string='ETA QR Code', compute='_compute_eta_qr_code_str')
    l10n_eg_submission_number = fields.Char(string='Submission ID', compute='_compute_eta_response_data', store=True, copy=False)
    l10n_eg_uuid = fields.Char(string='Document UUID', compute='_compute_eta_response_data', store=True, copy=False)
    l10n_eg_eta_json_doc_file = fields.Binary(
        string='ETA JSON Document',
        attachment=True,
        copy=False,
    )
    l10n_eg_signing_time = fields.Datetime('Signing Time', copy=False)
    l10n_eg_is_signed = fields.Boolean(copy=False)

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move", "l10n_eg_uuid"):
            create_column(self.env.cr, "account_move", "l10n_eg_uuid", "VARCHAR")
            # Since l10n_eg_uuid columns does not exist we can assume l10n_eg_submission_number doesn't exist either
            create_column(self.env.cr, "account_move", "l10n_eg_submission_number", "VARCHAR")
        return super()._auto_init()

    @api.depends('l10n_eg_eta_json_doc_file')
    def _compute_eta_long_id(self):
        for rec in self:
            response_data = rec.l10n_eg_eta_json_doc_file and json.loads(base64.b64decode(rec.l10n_eg_eta_json_doc_file)).get('response')
            if response_data:
                rec.l10n_eg_long_id = response_data.get('l10n_eg_long_id')
            else:
                rec.l10n_eg_long_id = False

    @api.depends('invoice_date', 'l10n_eg_uuid', 'l10n_eg_long_id')
    def _compute_eta_qr_code_str(self):
        for move in self:
            if move.invoice_date and move.l10n_eg_uuid and move.l10n_eg_long_id:
                is_prod = move.company_id.l10n_eg_production_env
                base_url = self.env['account.edi.format']._l10n_eg_get_eta_qr_domain(production_enviroment=is_prod)
                qr_code_str = '%s/documents/%s/share/%s' % (base_url, move.l10n_eg_uuid, move.l10n_eg_long_id)
                move.l10n_eg_qr_code = qr_code_str
            else:
                move.l10n_eg_qr_code = ''

    @api.depends('l10n_eg_eta_json_doc_file')
    def _compute_eta_response_data(self):
        for rec in self:
            response_data = rec.l10n_eg_eta_json_doc_file and json.loads(base64.b64decode(rec.l10n_eg_eta_json_doc_file)).get('response')
            if response_data:
                rec.l10n_eg_uuid = response_data.get('l10n_eg_uuid')
                rec.l10n_eg_submission_number = response_data.get('l10n_eg_submission_number')
            else:
                rec.l10n_eg_uuid = False
                rec.l10n_eg_submission_number = False

    def _get_fields_to_detach(self):
        fields_list = super()._get_fields_to_detach()
        fields_list.append('l10n_eg_eta_json_doc_file')
        return fields_list

    def button_draft(self):
        self.l10n_eg_is_signed = False
        return super().button_draft()

    def action_post_sign_invoices(self):
        # only sign invoices that are confirmed and not yet sent to the ETA.
        invoices = self.filtered(lambda r: r.country_code == 'EG' and r.state == 'posted' and not r.l10n_eg_submission_number and r.edi_document_ids.filtered(lambda e: e.edi_format_id.code == 'eg_eta'))
        if not invoices:
            return

        company_ids = invoices.mapped('company_id')
        # since the middleware accepts only one drive at a time, we have to limit signing to one company at a time
        if len(company_ids) > 1:
            raise UserError(_('Please only sign invoices from one company at a time'))

        company_id = company_ids[0]
        drive_id = self.env['l10n_eg_edi.thumb.drive'].search([('user_id', '=', self.env.user.id),
                                                               ('company_id', '=', company_id.id)])

        if not drive_id:
            raise ValidationError(_('Please setup a personal drive for company %s', company_id.name))

        if not drive_id.certificate:
            raise ValidationError(_('Please setup the certificate on the thumb drive menu'))

        invoices.write({'l10n_eg_signing_time': datetime.utcnow()})

        for invoice in invoices:
            eta_invoice = self.env['account.edi.format']._l10n_eg_eta_prepare_eta_invoice(invoice)
            self.env['ir.attachment'].create({
                    'name': _('ETA_INVOICE_DOC_%s', invoice.name),
                    'res_id': invoice.id,
                    'res_model': invoice._name,
                    'res_field': 'l10n_eg_eta_json_doc_file',
                    'type': 'binary',
                    'raw': json.dumps(dict(request=eta_invoice)),
                    'mimetype': 'application/json',
                    'description': _('Egyptian Tax authority JSON invoice generated for %s.', invoice.name),
                })
            invoice.invalidate_recordset(fnames=['l10n_eg_eta_json_doc_file'])
        return drive_id.action_sign_invoices(invoices)

    def action_get_eta_invoice_pdf(self):
        """ This is a pdf with the structure from the government.  While we can use our own format,
        some clients appreciate this to verify that all the data is there in case of confusion."""
        self.ensure_one()
        eta_invoice_pdf = self.env['account.edi.format']._l10n_eg_get_eta_invoice_pdf(self)
        if eta_invoice_pdf.get('error', False):
            _logger.warning('PDF Content Error:  %s.', eta_invoice_pdf.get('error'))
            return
        self.message_post(
            body=_('ETA invoice has been received'),
            attachments=[('ETA invoice of %s.pdf' % self.name, eta_invoice_pdf.get('data'))]
        )

    def _l10n_eg_edi_exchange_currency_rate(self):
        """ Calculate the rate based on the balance and amount_currency, so we recuperate the one used at the time"""
        self.ensure_one()
        from_currency = self.currency_id
        to_currency = self.company_id.currency_id
        if from_currency != to_currency and self.invoice_line_ids:
            amount_currency = self.invoice_line_ids[0].amount_currency
            if not float_is_zero(amount_currency, precision_rounding=from_currency.rounding):
                return abs(self.invoice_line_ids[0].balance / amount_currency)
        return 1.0
