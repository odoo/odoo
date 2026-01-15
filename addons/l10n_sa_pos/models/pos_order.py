# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.addons.l10n_sa.models.account_move import ADJUSTMENT_REASONS
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_sa_reason = fields.Selection(string="ZATCA Reason", selection=ADJUSTMENT_REASONS)
    l10n_sa_reason_value = fields.Char(compute='_compute_l10n_sa_reason_value')

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.company_id.country_id.code == 'SA':
            mapped_reasons = self.mapped('l10n_sa_reason')
            if len(set(mapped_reasons)) > 1:
                raise UserError(_(
                    "You cannot create a consolidated invoice for POS orders with different"
                    " ZATCA refund reasons."
                ))
            confirmation_datetime = self.date_order if len(self) == 1 else fields.Datetime.now()
            vals.update({
                'l10n_sa_confirmation_datetime': confirmation_datetime,
                'l10n_sa_reason': mapped_reasons[0] if mapped_reasons else False,
            })
        return vals

    @api.depends("l10n_sa_reason")
    def _compute_l10n_sa_reason_value(self):
        for record in self:
            record.l10n_sa_reason_value = dict(self._fields['l10n_sa_reason']._description_selection(self.env)).get(record.l10n_sa_reason)
