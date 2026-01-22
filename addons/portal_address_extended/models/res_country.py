# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCountry(models.Model):
    _inherit = 'res.country'

    def _enforce_city_choice(self):
        if not self:
            return False

        # Only enabled on frontend for those countries for now
        # Feature has to be adapted to be more generic and less blocking
        # before being enabled for other countries
        if self.code not in ['BR', 'CL', 'PE', 'CO', 'TW']:
            return False

        self.ensure_one()
        return self.enforce_cities and bool(
            self.env['res.city'].sudo().search_count([('country_id', '=', self.id)], limit=1)
        )

    def _get_cities(self, state_id=None):
        if not self:
            return self.env['res.city'].sudo()

        return self.env['res.city'].sudo().search([
            ('country_id', '=', self.id),
            ('state_id', 'in', [state_id, False]),
        ])

    def _get_cities_fields_to_fetch(self):
        return ['id', 'name', 'state_id']
