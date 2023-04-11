from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_installed = fields.Boolean(compute='_compute_l10n_installed')

    @api.depends('country_id')
    def _compute_l10n_installed(self):
        for company in self:
            company.l10n_installed = company.country_id.l10n_module_id.state in (False, 'installed')

    def install_l10n(self):
        self.country_id.l10n_module_id.button_immediate_install()
