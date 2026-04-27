from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_co_edi_pos_dian_enabled = fields.Boolean(compute='_compute_l10n_co_edi_pos_dian_enabled')

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['l10n_co_edi_pos_dian_enabled']

    @api.depends('account_fiscal_country_id.code', 'l10n_co_dian_provider')
    def _compute_l10n_co_edi_pos_dian_enabled(self):
        for company in self:
            company.l10n_co_edi_pos_dian_enabled = company.account_fiscal_country_id.code == 'CO' and company.l10n_co_dian_provider == 'dian'
