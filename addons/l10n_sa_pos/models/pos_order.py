# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.l10n_sa.models.account_move import ADJUSTMENT_REASONS


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_sa_reason = fields.Selection(string="ZATCA Reason", selection=ADJUSTMENT_REASONS)
    l10n_sa_reason_value = fields.Char(compute='_compute_l10n_sa_reason_value')

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.company_id.country_id.code == 'SA':
            vals.update({
                'l10n_sa_confirmation_datetime': self.date_order,
                'l10n_sa_reason': self.l10n_sa_reason,
            })
        return vals

    @api.depends("l10n_sa_reason")
    def _compute_l10n_sa_reason_value(self):
        for record in self:
            record.l10n_sa_reason_value = dict(self._fields['l10n_sa_reason']._description_selection(self.env)).get(record.l10n_sa_reason)
