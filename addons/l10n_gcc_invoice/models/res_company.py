from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_gcc_dual_language_invoice = fields.Boolean(string="GCC Formatted Invoices")
    l10n_gcc_country_is_gcc = fields.Boolean(compute='_compute_l10n_gcc_country_is_gcc')

    @api.depends('partner_id.country_id.country_group_ids.code')
    def _compute_l10n_gcc_country_is_gcc(self):
        for record in self:
            record.l10n_gcc_country_is_gcc = record.country_id and 'GCC' in record.country_id.country_group_codes
