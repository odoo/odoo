# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pe_financial_statement_type = fields.Selection(related="company_id.l10n_pe_financial_statement_type", readonly=False)
    l10n_pe_fs_type_warning = fields.Text(compute='_compute_l10n_pe_fs_type_warning')

    @api.depends('l10n_pe_financial_statement_type')
    def _compute_l10n_pe_fs_type_warning(self):
        for record in self:
            if record.l10n_pe_financial_statement_type:
                record.l10n_pe_fs_type_warning = _("Changing FST will reset FS Rubrics on all company accounts. Make sure to add FS Rubric to each account after changing the FST to correctly export inventory and balance reports.")
            else:
                record.l10n_pe_fs_type_warning = False
