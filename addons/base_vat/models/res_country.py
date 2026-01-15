# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResCountry(models.Model):
    _inherit = 'res.country'

    has_foreign_fiscal_position = fields.Boolean(compute='_compute_has_foreign_fiscal_position')  # Caching technical field

    @api.depends_context('company')
    def _compute_has_foreign_fiscal_position(self):
        for country in self:
            country.has_foreign_fiscal_position = self.env['account.fiscal.position'].search([
                *self._check_company_domain(self.env.company),
                ('foreign_vat', '!=', False),
                ('country_id', '=', country.id),
            ], limit=1)
