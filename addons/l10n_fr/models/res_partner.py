# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    siret = fields.Char(string='SIRET', size=14)

    @api.model
    def _get_company_registry_label(self, country_code):
        self.ensure_one()
        if country_code == 'FR':
            return 'SIREN'
        else:
            return super()._get_company_registry_label(country_code)
