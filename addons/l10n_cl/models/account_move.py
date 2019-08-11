# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_latam_document_type_id_code = fields.Char(related='l10n_latam_document_type_id.code', string='Doc Type')
    partner_id_vat = fields.Char(related='partner_id.vat', string='VAT No')
    l10n_latam_internal_type = fields.Selection(related='l10n_latam_document_type_id.internal_type',
                                                string='L10n Latam Internal Type')

    def get_document_type_sequence(self):
        """ Return the match sequences for the given journal and invoice """
        self.ensure_one()
        if self.journal_id.l10n_latam_use_documents and self.l10n_latam_country_code == 'CL':
            res = self.journal_id.l10n_cl_sequence_ids.filtered(
                lambda x: x.l10n_latam_document_type_id == self.l10n_latam_document_type_id)
            return res
        return super().get_document_type_sequence()

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if (self.journal_id.l10n_latam_use_documents and
                self.journal_id.company_id.country_id == self.env.ref('base.cl')):
            domain += [('active', '=', True)]
            sequences = self.env['ir.sequence'].search([('l10n_latam_journal_id', '=', self.journal_id.id)])
            if sequences:
                domain += [
                    ('id', 'in', sequences.l10n_latam_document_type_id.ids)
                ]
        return domain
