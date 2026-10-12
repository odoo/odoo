# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def write(self, vals):
        fr_before = self.filtered('is_france_country')
        result = super().write(vals)
        fr_after = self.filtered('is_france_country')
        if updated_companies := (fr_before - fr_after) + (fr_after - fr_before):
            providers = (
                self.env['payment.provider'].sudo().search([
                    ('code', '=', 'worldline'),
                    ('company_id', 'in', updated_companies.ids),
                ])
                or self.env.ref('payment.payment_provider_worldline').sudo().filtered(
                    lambda provider: provider.company_id in updated_companies
                )
            )
            if providers:
                providers._apply_worldline_branding()
        return result
