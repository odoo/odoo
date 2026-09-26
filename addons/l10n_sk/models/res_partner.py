# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    additional_identifiers = fields.Json(inverse='_inverse_additional_identifiers')

    def _inverse_additional_identifiers(self):
        companies = self.env['res.company'].search([('partner_id', 'in', self.ids)])
        for company in companies:
            value = company.partner_id._get_additional_identifier('SK_TIN')
            if value and company.income_tax_id != value:
                company.income_tax_id = value
