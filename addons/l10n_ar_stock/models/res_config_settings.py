from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ar_arba_cit = fields.Char(related='company_id.l10n_ar_arba_cit', readonly=False)
    l10n_ar_arba_cot_environment = fields.Selection(related='company_id.l10n_ar_arba_cot_environment', readonly=False)
    l10n_ar_arba_cot_uses_parent = fields.Boolean(compute='_compute_l10n_ar_arba_cot_uses_parent')

    @api.depends('company_id')
    def _compute_l10n_ar_arba_cot_uses_parent(self):
        for settings in self:
            company = settings.company_id
            settings.l10n_ar_arba_cot_uses_parent = company.sudo()._l10n_ar_get_arba_cot_company() != company
