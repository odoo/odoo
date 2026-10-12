# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id:
                raise UserError(_("You have to set a country in your company setting."))
        return super().open_ui()

    @api.model
    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)

        if data and self.env.company.country_id.code == 'SA':
            l10n_sa_reason_field = self.env['ir.model.fields']._get('account.move', 'l10n_sa_reason')
            data[0]['_zatca_refund_reasons'] = [
                {'value': refund_reason.value, 'name': refund_reason.name}
                for refund_reason in l10n_sa_reason_field.selection_ids
            ]

        return data
