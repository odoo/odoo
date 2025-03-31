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

    @api.depends('move_type', 'company_id', 'invoice_line_ids.tax_ids')
    def _compute_l10n_es_edi_is_required(self):
        for move in self:
            has_tax = True
            # Check it is not an importation invoice (which will be report through the DUA invoice)
            if move.is_purchase_document():
                taxes = move.invoice_line_ids.tax_ids
                has_tax = any(t.l10n_es_type and t.l10n_es_type != 'ignore' for t in taxes)
            move.l10n_es_edi_is_required = move.is_invoice() \
                                           and move.country_code == 'ES' \
                                           and move.company_id.l10n_es_sii_tax_agency \
                                           and has_tax

    def _l10n_es_is_dua(self):
        self.ensure_one()
        return any(t.l10n_es_type == 'dua' for t in self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy())

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
