# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_edi_is_required = fields.Boolean(
        string="Is the Spanish EDI needed",
        compute='_compute_l10n_es_edi_is_required'
    )
    l10n_es_edi_csv = fields.Char(string="CSV return code", copy=False, tracking=True)
    # Technical field to keep the date the invoice was sent the first time as
    # the date the invoice was registered into the system.
    l10n_es_registration_date = fields.Date(
        string="Registration Date", copy=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'company_id')
    def _compute_l10n_es_edi_is_required(self):
        for move in self:
            move.l10n_es_edi_is_required = move.is_invoice() \
                                           and move.country_code == 'ES' \
                                           and move.company_id.l10n_es_edi_tax_agency

    def _check_edi_documents_for_reset_to_draft(self):
        docs = self.edi_document_ids.filtered(lambda d: d.edi_format_id._needs_web_services())
        if len(docs) == 1 and docs.edi_format_id.code == 'es_sii' and docs.state != 'to_cancel':
            return True
        return super()._check_edi_documents_for_reset_to_draft()

    def _edi_allow_button_draft(self):
        docs = self.edi_document_ids.filtered(lambda d: d.edi_format_id._needs_web_services())
        if len(docs) == 1 and docs.edi_format_id.code == 'es_sii' and docs.state != 'to_cancel':
            return True
        return super()._edi_allow_button_draft()
