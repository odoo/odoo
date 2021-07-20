# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools.misc import formatLang

from datetime import date, timedelta

class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ec_sri_payment_id = fields.Many2one('l10n.ec.sri.payment', _("Payment Method (SRI)"))
    l10n_ec_access_key = fields.Char(_("Authorization"), copy=False)
    l10n_ec_auth_type = fields.Selection(related="l10n_latam_document_type_id.l10n_ec_authorization")
    l10n_ec_is_electronic = fields.Boolean(default=False, compute="_l10n_ec_is_electronic")

    def _get_l10n_latam_documents_domain(self):
        #Filter document types according to ecuadorian move_type
        domain = super(AccountMove, self)._get_l10n_latam_documents_domain()
        if self.country_code == 'EC':
            if self.move_type in ['out_invoice']:
                domain.extend([('l10n_ec_type', '=', 'out_invoice')])
            if self.move_type in ['out_refund']:
                domain.extend([('l10n_ec_type', '=', 'out_refund')])
            if self.move_type in ['in_invoice']:
                domain.extend([('l10n_ec_type', '=', 'in_invoice')])
            if self.move_type in ['in_refund']:
                domain.extend([('l10n_ec_type', '=', 'in_refund')])
        return domain

    @api.depends('journal_id', 'partner_id')
    def _l10n_ec_is_electronic(self):
        self.ensure_one()
        self.l10n_ec_is_electronic = len(self.journal_id.edi_format_ids) > 0

    def _get_formatted_sequence(self, number=0):
        return "%s %s-%s-%09d" % (self.l10n_latam_document_type_id.doc_code_prefix,
                                    self.journal_id.l10n_ec_entity,
                                    self.journal_id.l10n_ec_emission,
                                    number)

    def _get_starting_sequence(self):
        """ If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number """
        if self.journal_id.l10n_latam_use_documents and self.env.company.country_id.code == "EC":
            if self.l10n_latam_document_type_id:
                return self._get_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.company_id.country_id.code == "EC":
                        
            where_string += " AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s"
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0

        return where_string, param
