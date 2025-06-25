# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        """ If exists, use specific vat identification.type for the country of the company """
        companies = super().create(vals_list)
        for company in companies:
            if not company.country_id:
                continue
            country_vat_type = self.env['l10n_latam.identification.type'].search(
                [('is_vat', '=', True), ('country_id', '=', company.country_id.id)], limit=1)
            if country_vat_type:
                company.partner_id.l10n_latam_identification_type_id = country_vat_type
        return companies
