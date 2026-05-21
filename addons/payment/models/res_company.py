# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)

        # Duplicate installed providers in the new companies.
        providers_sudo = self.env['payment.provider'].sudo().search(
            [('company_id', '=', self.env.user.company_id.id), ('module_state', '=', 'installed')]
        )
        for company in companies:
            for provider_sudo in providers_sudo:
                provider_sudo.copy({'company_id': company.id})

        return companies
