# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        # OVERRIDE to load the MX EDI fields when loading the pos data (load_pos_data)
        vals = super()._loader_params_res_partner()
        if self.company_id.country_code == 'MX':
            vals['search_params']['fields'] += ['l10n_mx_edi_fiscal_regime', 'l10n_mx_edi_usage', 'l10n_mx_edi_no_tax_breakdown', 'country_code']
        return vals

    def _pos_data_process(self, loaded_data):
        # OVERRIDE to load the possible values for the field 'l10n_mx_edi_fiscal_regime'
        super()._pos_data_process(loaded_data)
        if self.company_id.country_code == 'MX':
            l10n_mx_edi_fiscal_regime = self.env['ir.model.fields']._get('res.partner', 'l10n_mx_edi_fiscal_regime')
            loaded_data['l10n_mx_edi_fiscal_regime'] = [{'value': s.value, 'name': s.name} for s in l10n_mx_edi_fiscal_regime.selection_ids]
            l10n_mx_edi_usage = self.env['ir.model.fields']._get('account.move', 'l10n_mx_edi_usage')
            loaded_data['l10n_mx_edi_usage'] = [{'value': s.value, 'name': s.name} for s in l10n_mx_edi_usage.selection_ids]
            loaded_data['l10n_mx_country_id'] = self.env['res.country'].search([('code', '=', 'MX')], limit=1).id
