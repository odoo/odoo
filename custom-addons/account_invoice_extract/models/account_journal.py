# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    alias_auto_extract_pdfs_only = fields.Boolean(
        string='Auto extract PDFs only',
        help='Only extract PDF files attached to email arriving trough this email alias.',
    )

    display_alias_auto_extract_pdfs_only = fields.Boolean(
        compute='_compute_display_alias_auto_extract_pdfs_only',
    )

    @api.depends('company_id')
    def _compute_display_alias_auto_extract_pdfs_only(self):
        for journal in self:
            if journal.type == 'purchase':
                journal.display_alias_auto_extract_pdfs_only = journal.company_id.extract_in_invoice_digitalization_mode == 'auto_send'
            elif journal.type == 'sale':
                journal.display_alias_auto_extract_pdfs_only = journal.company_id.extract_out_invoice_digitalization_mode == 'auto_send'
            else:
                journal.display_alias_auto_extract_pdfs_only = False
