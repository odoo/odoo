# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCountry(models.Model):
    _inherit = 'res.country'

    def _get_cities(self, state_id=None):
        if self.code == 'BR' and not state_id:
            return self.env['res.city'].sudo().search([('country_id', '=', self.id)])
        return super()._get_cities(state_id)

    def _get_cities_fields_to_fetch(self):
        res = super()._get_cities_fields_to_fetch()
        if self.code == 'BR':
            res += ['l10n_br_zip_ranges']

        return res
