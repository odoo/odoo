# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        """ If exists, use specific vat identification.type for the country of the company """
        country_id = vals.get('country_id')
        if country_id:
            country_vat_type = self.env['l10n_latam.identification.type'].search(
                [('is_vat', '=', True), ('country_id', '=', country_id)], limit=1)
            if country_vat_type:
                self = self.with_context(default_l10n_latam_identification_type_id=country_vat_type.id)
        return super().create(vals)
