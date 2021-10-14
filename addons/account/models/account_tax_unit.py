# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, Command, _
from odoo.exceptions import ValidationError


class AccountTaxUnit(models.Model):
    _name = "account.tax.unit"
    _description = "Tax Unit"

    name = fields.Char(string="Name", required=True)
    country_id = fields.Many2one(string="Country", comodel_name='res.country', required=True, help="The country in which this tax unit is used to group your companies' tax reports declaration.")
    vat = fields.Char(string="Tax ID", required=True, help="The identifier to be used when submitting a report for this unit.")
    company_ids = fields.Many2many(string="Companies", comodel_name='res.company', required=True, help="Members of this unit")
    main_company_id = fields.Many2one(string="Main Company", comodel_name='res.company', required=True, help="Main company of this unit; the one actually reporting and paying the taxes.")

    @api.model_create_multi
    def create(self, vals_list):
        created_units = super().create(vals_list)
        created_units._assign_no_tax_fiscal_positions()
        return created_units

    def write(self, vals):
        res = super().write(vals)
        if 'company_ids' in vals:
            self._assign_no_tax_fiscal_positions()
        return res

    def _assign_no_tax_fiscal_positions(self):
        for record in self:
            for company in record.company_ids:
                existing_fp = self.env.ref('account.tax_unit_fp_%s' % company.id, raise_if_not_found=False)
                if not existing_fp:
                    existing_fp = self.env['account.fiscal.position'].sudo().create({
                        'name': self.name,
                        'company_id': company.id
                    })
                    self.env['ir.model.data'].create({
                        'name': 'tax_unit_fp_%s' % company.id,
                        'module': 'account',
                        'model': 'account.fiscal.position',
                        'res_id': existing_fp.id,
                        'noupdate': True,
                    })
                sales_taxes_to_map = self.env['account.tax'].search([
                    ('type_tax_use', '=', 'sale'),
                    ('amount_type', '=', 'percent'),
                    ('company_id', '=', company.id),
                    ('id', 'not in', existing_fp.mapped('tax_ids.tax_src_id').ids)
                ])
                existing_fp.write({'tax_ids': [Command.create({'tax_src_id': tax.id}) for tax in sales_taxes_to_map]})
                for c in record.company_ids - company:
                    c.partner_id.sudo().with_company(company).property_account_position_id = existing_fp

    @api.constrains('country_id', 'company_ids')
    def _validate_companies_country(self):
        for record in self:
            currencies = set()
            for company in record.company_ids:
                currencies.add(company.currency_id)

                if any(unit != record and unit.country_id == record.country_id for unit in company.account_tax_unit_ids):
                    raise ValidationError(_("Company %s already belongs to a tax unit in %s. A company can at most be part of one tax unit per country.", company.name, record.country_id.name))

            if len(currencies) > 1:
                raise ValidationError(_("A tax unit can only be created between companies sharing the same main currency."))

    @api.constrains('company_ids', 'main_company_id')
    def _validate_main_company(self):
        for record in self:
            if record.main_company_id not in record.company_ids:
                raise ValidationError(_("The main company of a tax unit has to be part of it."))

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        for record in self:
            if not record.main_company_id and record.company_ids:
                record.main_company_id = record.company_ids[0]
