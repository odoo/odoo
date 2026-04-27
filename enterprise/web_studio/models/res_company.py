# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    background_image = fields.Binary(string="Home Menu Background Image", attachment=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Override to ensure a default exists for all studio-created company/currency fields."""
        companies = super().create(vals_list)
        company_fields = self.env['ir.model.fields'].sudo().search([
            ('name', 'in', ['x_studio_company_id', "x_company_id"]),
            ('ttype', '=', 'many2one'),
            ('relation', '=', 'res.company'),
            ('store', '=', True),
            ('state', '=', 'manual')
        ])
        for new_company in companies:
            for company_field in company_fields:
                self.env['ir.default'].set(company_field.model_id.model, company_field.name,
                                        new_company.id, company_id=new_company.id)
        currency_fields = self.env['ir.model.fields'].sudo().search([
            ('name', '=', 'x_studio_currency_id'),
            ('ttype', '=', 'many2one'),
            ('relation', '=', 'res.currency'),
            ('store', '=', True),
            ('state', '=', 'manual')
        ])
        for new_company in companies:
            for currency_field in currency_fields:
                self.env['ir.default'].set(currency_field.model_id.model, currency_field.name,
                                        new_company.currency_id.id,company_id=new_company.id)
        return companies
