# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrTdsCalculation(models.TransientModel):
    _name = 'l10n.in.tds.computation.wizard'
    _description = 'Indian Payroll: TDS computation'

    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.company.country_id.code != "IN":
            raise UserError(_('You must be logged in a Indian company to use this feature'))
        if not res.get('contract_id') and self.env.context.get('active_id') and self.env.context.get('active_model') == 'hr.contract':
            res['contract_id'] = self.env.context['active_id']
            contract_id = self.env['hr.contract'].browse(res['contract_id'])
            res['payslip_id'] = self.env['hr.payslip'].search([
                ('contract_id', '=', contract_id.id),
                ('employee_id', '=', contract_id.employee_id.id),
                ('date_from', '>=', contract_id.date_start),
                ('state', 'in', ['done', 'paid']),
            ], limit=1, order='date_from desc').id
        if not res.get('currency_id') and self.env.company.currency_id:
            res['currency_id'] = self.env.company.currency_id.id
        if not res.get('standard_deduction'):
            # Clearing the cache because the changes made to the parameter value are not being reflected here.
            self.env.registry.clear_cache()
            res['standard_deduction'] = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_in_standard_deduction')
        return res

    contract_id = fields.Many2one('hr.contract')
    payslip_id = fields.Many2one('hr.payslip')
    currency_id = fields.Many2one("res.currency", string='Currency')
    total_income = fields.Float(string="Total Income(Year)", compute="_compute_total_income", readonly=False)
    standard_deduction = fields.Float(string="Standard Deduction", readonly=True)
    taxable_income = fields.Float(string="Taxable Income", compute="_compute_taxable_income")
    tax_on_taxable_income = fields.Float(string="Tax on Taxable Income", compute="_compute_taxable_income")
    rebate = fields.Float(string="Rebate Under Section 87A(a)", compute="_compute_taxable_income",
                          help="Reduces tax liability for resident individuals with income up to ₹7 lakh (New Regime)")
    total_tax_on_income = fields.Float(string="Total Tax on Income", compute="_compute_taxable_income")
    surcharge = fields.Float(string="Surcharge", compute="_compute_taxable_income")
    cess = fields.Float(string="Health and Education Cess", compute="_compute_taxable_income", help="4% of Tax on Taxable Income + Surcharge")
    total_tax = fields.Float(string="Total Tax to be Paid", compute="_compute_taxable_income")
    net_monthly = fields.Float(string="Monthly Net Payable", compute="_compute_net_monthly")
    tds_monthly = fields.Float(string="Monthly TDS Payable", compute="_compute_tds_monthly", readonly=False, store=True)

    @api.depends('contract_id', 'total_income')
    def _compute_net_monthly(self):
        for record in self:
            record.net_monthly = record.payslip_id.net_wage or record.total_income / 12

    @api.depends('net_monthly')
    def _compute_total_income(self):
        for record in self:
            record.total_income = record.net_monthly * 12

    @api.depends('total_income')
    def _compute_taxable_income(self):
        rule_parameter = self.env['hr.rule.parameter']
        tax_slabs = rule_parameter._get_parameter_from_code('l10n_in_tds_rate_chart')
        tax_slabs_for_surcharge = rule_parameter._get_parameter_from_code('l10n_in_surcharge_rate')
        min_income_for_surcharge = rule_parameter._get_parameter_from_code('l10n_in_min_income_surcharge')
        min_income_for_rebate = rule_parameter._get_parameter_from_code('l10n_in_min_income_tax_rebate')

        for record in self:
            record.taxable_income = max(record.total_income - record.standard_deduction, 0)

            tax = 0
            for rate, (lower, upper) in tax_slabs:
                if record.taxable_income <= lower:
                    break
                taxable_amount = min(record.taxable_income, float(upper)) - lower
                tax += round(taxable_amount * rate)
            record.tax_on_taxable_income = tax

            if record.taxable_income >= min_income_for_rebate:
                marginal_income = record.taxable_income - min_income_for_rebate
                record.rebate = max(record.tax_on_taxable_income - marginal_income, 0)
            else:
                record.rebate = record.tax_on_taxable_income
            record.total_tax_on_income = record.tax_on_taxable_income - record.rebate

            if record.taxable_income > min_income_for_surcharge:
                surcharge = 0
                for rate, amount in tax_slabs_for_surcharge:
                    if record.taxable_income <= float(amount[1]):
                        surcharge = record.total_tax_on_income * rate
                        break

                max_tax_slabs = rule_parameter._get_parameter_from_code('l10n_in_max_surcharge_tax_rate')
                max_taxable_income, max_tax, max_surcharge = 0, 0, 0

                for income, tax, surcharge_rate in max_tax_slabs:
                    if record.taxable_income <= income:
                        break
                    else:
                        max_taxable_income, max_tax, max_surcharge = income, tax, surcharge_rate

                excess_income = record.taxable_income - max_taxable_income
                max_tax_with_surcharge = max_tax + max_surcharge
                total_tax_with_surcharge = record.total_tax_on_income + surcharge
                excess_tax = total_tax_with_surcharge - max_tax_with_surcharge

                if excess_tax - excess_income > 0:
                    record.surcharge = max_tax_with_surcharge + record.taxable_income - max_taxable_income - record.total_tax_on_income
                else:
                    record.surcharge = surcharge
            else:
                record.surcharge = 0.0

            record.cess = (record.total_tax_on_income + record.surcharge) * 0.04
            record.total_tax = record.total_tax_on_income + record.cess + record.surcharge

    @api.depends('total_tax')
    def _compute_tds_monthly(self):
        for record in self:
            record.tds_monthly = record.total_tax / 12

    def set_tds_on_contracts(self):
        for record in self:
            record.contract_id.l10n_in_tds = record.tds_monthly
