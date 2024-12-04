from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    l10n_in_tds_tcs_section_id = fields.Many2one('l10n_in.section.alert', string="TCS/TDS Section")
    l10n_in_tds_feature_enabled = fields.Boolean(compute='_compute_tds_tcs_features', store=True)
    l10n_in_tcs_feature_enabled = fields.Boolean(compute='_compute_tds_tcs_features', store=True)

    @api.depends('company_ids.l10n_in_tds_feature', 'company_ids.l10n_in_tcs_feature')
    def _compute_tds_tcs_features(self):
        for record in self:
            record.l10n_in_tds_feature_enabled = any(company.l10n_in_tds_feature for company in record.company_ids)
            record.l10n_in_tcs_feature_enabled = any(company.l10n_in_tcs_feature for company in record.company_ids)
