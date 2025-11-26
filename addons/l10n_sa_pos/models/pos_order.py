# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.company_id.country_id.code == 'SA':
            confirmation_datetime = self.date_order if len(self) == 1 else fields.Datetime.now()
            vals['l10n_sa_confirmation_datetime'] = confirmation_datetime
        return vals
