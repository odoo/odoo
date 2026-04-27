# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        l10n_mx_edi_fiscal_regime = self.env['ir.model.fields']._get('res.partner', 'l10n_mx_edi_fiscal_regime')
        l10n_mx_edi_usage = self.env['ir.model.fields']._get('account.move', 'l10n_mx_edi_usage')
        data['data'][0]['_l10n_mx_edi_fiscal_regime'] = [{'value': s.value, 'name': s.name} for s in l10n_mx_edi_fiscal_regime.selection_ids]
        data['data'][0]['_l10n_mx_edi_usage'] = [{'value': s.value, 'name': s.name} for s in l10n_mx_edi_usage.selection_ids]
        data['data'][0]['_l10n_mx_country_id'] = self.env['res.country'].search([('code', '=', 'MX')], limit=1).id
        return data
