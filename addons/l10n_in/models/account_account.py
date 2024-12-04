from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    company_id = fields.Many2one('res.company', compute='_compute_company_id', store=True)
    l10n_in_tds_tcs_section_id = fields.Many2one('l10n_in.section.alert', string="TCS/TDS Section")
    l10n_in_tds_feature_enabled = fields.Boolean(related='company_id.l10n_in_tds_feature')
    l10n_in_tcs_feature_enabled = fields.Boolean(related='company_id.l10n_in_tcs_feature')

    @api.depends_context('company')
    def _compute_company_id(self):
        for rec in self:
            rec.company_id = self.env.company
