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
    fpos_synced = fields.Boolean(string="Fiscal Positions Synchronised", compute='_compute_fiscal_position_completion', help="Technical field indicating whether Fiscal Positions exist for all companies in the unit")

    @api.depends('company_ids')
    def _compute_fiscal_position_completion(self):
        for unit in self:
            synced = True
            for company in unit.company_ids:
                origin_company = company._origin if isinstance(company.id, models.NewId) else company
                fp = unit._get_tax_unit_fiscal_positions(companies=origin_company)
                all_partners_with_fp = self.env['res.company'].search([]).with_company(origin_company).partner_id\
                    .filtered(lambda p: p.property_account_position_id == fp) if fp else self.env['res.partner']
                synced = all_partners_with_fp == (unit.company_ids - origin_company).partner_id
                if not synced:
                    break
            unit.fpos_synced = synced

    def _get_tax_unit_fiscal_positions(self, companies, create_or_refresh=False):
        """
        Retrieves or creates fiscal positions for all companies specified.
        Each Fiscal Position contains all the taxes of the company mapped to no tax

        @param {recordset} companies: companies for which to find/create fiscal positions
        @param {boolean} create_or_refresh: a boolean indicating whether the fiscal positions should be created if not found
        @return {recordset} all the fiscal positions found/created for the companies requested.
        """
        fiscal_positions = self.env['account.fiscal.position'].with_context(allowed_company_ids=self.env.user.company_ids.ids)
        for unit in self:
            for company in companies:
                fp_identifier = 'account.tax_unit_%s_fp_%s' % (unit.id, company.id)
                existing_fp = self.env.ref(fp_identifier, raise_if_not_found=False)
                if create_or_refresh:
                    taxes_to_map = self.env['account.tax'].with_context(
                        allowed_company_ids=self.env.user.company_ids.ids,
                    ).search(self.env['account.tax']._check_company_domain(company))
                    data = {
                        'xml_id': fp_identifier,
                        'values': {
                            'name': unit.name,
                            'company_id': company.id,
                            'tax_ids': [Command.clear()] + [Command.create({'tax_src_id': tax.id}) for tax in taxes_to_map]
                        }
                    }
                    existing_fp = fiscal_positions._load_records([data])
                if existing_fp:
                    fiscal_positions += existing_fp
        return fiscal_positions

    def action_sync_unit_fiscal_positions(self):
        self._get_tax_unit_fiscal_positions(companies=self.env['res.company'].search([])).unlink()
        for unit in self:
            for company in unit.company_ids:
                fp = unit._get_tax_unit_fiscal_positions(companies=company, create_or_refresh=True)
                (unit.company_ids - company).with_company(company).partner_id.property_account_position_id = fp

    def unlink(self):
        # EXTENDS base
        self._get_tax_unit_fiscal_positions(companies=self.env['res.company'].search([])).unlink()
        return super().unlink()

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

    @api.constrains('company_ids')
    def _validate_companies(self):
        for record in self:
            if len(record.company_ids) < 2:
                raise ValidationError(_("A tax unit must contain a minimum of two companies. You might want to delete the unit."))

    @api.constrains('country_id', 'vat')
    def _validate_vat(self):
        for record in self:
            if not record.vat:
                continue

            checked_country_code = self.env['res.partner']._run_vat_test(record.vat, record.country_id)

            if checked_country_code and checked_country_code != record.country_id.code.lower():
                raise ValidationError(_("The country detected for this VAT number does not match the one set on this Tax Unit."))

            if not checked_country_code:
                tu_label = _("tax unit [%s]", record.name)
                error_message = self.env['res.partner']._build_vat_error_message(record.country_id.code.lower(), record.vat, tu_label)
                raise ValidationError(error_message)

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        if self.main_company_id not in self.company_ids and self.company_ids:
            self.main_company_id = self.company_ids[0]._origin
        elif not self.company_ids:
            self.main_company_id = False
