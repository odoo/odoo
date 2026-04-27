# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class L10nBeDoublePayRecoveryWizard(models.TransientModel):
    _name = 'l10n.be.double.pay.recovery.wizard'
    _description = 'CP200: Double Pay Recovery Wizard'

    @api.model
    def default_get(self, fields_list):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        result = super(L10nBeDoublePayRecoveryWizard, self).default_get(fields_list)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'hr.payslip':
            payslip_id = self.env.context['active_id']
            payslip = self.env['hr.payslip'].browse(payslip_id)
            result['payslip_id'] = payslip_id
            result['employee_id'] = payslip.employee_id.id
            result['contract_id'] = payslip.contract_id.id
        return result

    payslip_id = fields.Many2one('hr.payslip')
    employee_id = fields.Many2one('hr.employee')
    contract_id = fields.Many2one('hr.contract')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    line_ids = fields.One2many('l10n.be.double.pay.recovery.line.wizard', 'wizard_id', string="Occupation Lines",
        compute='_compute_line_ids', readonly=False, store=True)
    gross_salary = fields.Monetary(compute='_compute_gross_salary', store=True, readonly=False)
    company_calendar = fields.Many2one(related='company_id.resource_calendar_id')
    months_count = fields.Float(string="Current Occupation Duration (Months)", compute='_compute_months_count')
    months_count_description = fields.Char(string="Current Occupation Duration (Description)", compute='_compute_months_count')

    threshold = fields.Monetary(compute='_compute_amounts_to_recover', store=True, readonly=False)
    double_pay_to_recover = fields.Monetary(compute='_compute_amounts_to_recover', store=True, readonly=False)

    @api.depends('payslip_id.date_to', 'employee_id')
    def _compute_months_count(self):
        for wizard in self:
            date_from = wizard.employee_id.first_contract_date + relativedelta(day=1)
            if not date_from:
                raise UserError(_("This employee doesn't have a first contract date"))
            date_to = wizard.payslip_id.date_to + relativedelta(years=-1, month=12, day=31) + relativedelta(days=1)
            wizard.months_count = (date_to.year - date_from.year) * 12 + (date_to.month - date_from.month)
            if wizard.months_count > 12:
                wizard.months_count_description = _('The employee is occupied from the %(date_from)s to the %(date_to)s. There is nothing to recover as the employee is there for more than 12 months', date_from=format_date(self.env, date_from), date_to=format_date(self.env, wizard.payslip_id.date_to))
            else:
                wizard.months_count_description = _('The employee is occupied from the %(date_from)s to the %(date_to)s.', date_from=format_date(self.env, date_from), date_to=format_date(self.env, wizard.payslip_id.date_to))

    @api.depends('employee_id')
    def _compute_line_ids(self):
        # Copy the employee lines, but some fields only exist on the employee version not the wizard version
        fields_to_copy = (self.env['l10n.be.double.pay.recovery.line']._fields.keys() - {'employee_id', 'company_id'})
        previous_year = fields.Datetime.today().date().year - 1
        for wizard in self:
            # Copy the lines that are of the previous year
            wizard.write({'line_ids': [fields.Command.clear()] + [fields.Command.create(read_result)\
                for read_result in wizard.employee_id.double_pay_line_ids.filtered(lambda d: d.year and d.year == previous_year and d.year <= d.employee_id.first_contract_year).read(fields=fields_to_copy)]})

    @api.depends('contract_id')
    def _compute_gross_salary(self):
        for wizard in self:
            wizard.gross_salary = wizard.contract_id._get_contract_wage()

    @api.depends(
        'gross_salary', 'months_count', 'line_ids.months_count', 'line_ids.occupation_rate')
    def _compute_amounts_to_recover(self):
        for wizard in self:
            # Computation of the limit = Current monthly remuneration * number of months of
            # employment in the previous year * fraction of occupancy on the certificate * 7.67%
            # If vacation certificate amount < the limit: NO limit applicable
            wizard.threshold = sum(wizard.gross_salary * l.months_count * l.occupation_rate / 100.0 * 0.0767 for l in wizard.line_ids)

            # Calculation of amounts to be recovered
            wizard.double_pay_to_recover = min(wizard.threshold, sum(wizard.line_ids.mapped('amount')))

    def action_validate(self):
        self.ensure_one()
        self.payslip_id.write({
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_double_holiday_recovery').id,
                'amount': self.double_pay_to_recover,
            })],
        })
        self.payslip_id.compute_sheet()

class L10nBeDoublePayRecoveryLineWizard(models.TransientModel):
    _name = 'l10n.be.double.pay.recovery.line.wizard'
    _description = 'CP200: Double Pay Recovery Line Wizard'

    amount = fields.Monetary(string="Amount", required=True, help="Holiday pay amount on the holiday attest from the previous employer")
    occupation_rate = fields.Float(required=True, help="Included between 0 and 100%")
    currency_id = fields.Many2one(related='wizard_id.currency_id')
    wizard_id = fields.Many2one('l10n.be.double.pay.recovery.wizard')
    months_count = fields.Float(string="# Months")
    company_calendar = fields.Many2one(related='wizard_id.company_calendar')
    year = fields.Integer()
