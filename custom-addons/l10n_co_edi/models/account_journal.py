# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_co_edi_dian_authorization_number = fields.Char(string=u'Resolución de Facturación')
    l10n_co_edi_dian_authorization_date = fields.Date(string=u'Fecha de Resolución')
    l10n_co_edi_dian_authorization_end_date = fields.Date(string='Fecha de finalización Resolución')
    l10n_co_edi_min_range_number = fields.Integer(string='Range of numbering (minimum)')
    l10n_co_edi_max_range_number = fields.Integer(string='Range of numbering (maximum)')
    l10n_co_edi_debit_note = fields.Boolean(string='Nota de Débito')
    l10n_co_edi_is_support_document = fields.Boolean('Support Document', compute='_compute_l10n_co_edi_is_support_document', store=False)

    @api.depends('type', 'l10n_co_edi_dian_authorization_number')
    def _compute_l10n_co_edi_is_support_document(self):
        for record in self:
            if record.type == 'purchase' and record.l10n_co_edi_dian_authorization_number:
                record.l10n_co_edi_is_support_document = True
            else:
                record.l10n_co_edi_is_support_document = False
