# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain


class HrLeaveAccrualRule(models.Model):
    _name = 'hr.leave.accrual.rule'
    _description = 'Accrual Rule'
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    country_id = fields.Many2one('res.country', default=lambda self: self.env.company.country_id)
    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string='Time Type', required=True, ondelete='restrict',
        domain="[('requires_allocation', '=', True), ('time_off_selectable', '=', True)]")
    unit_of_measure = fields.Selection(related='work_entry_type_id.unit_of_measure')
    employee_domain = fields.Char(string='Employees', required=True, default='[]')
    frequency_count = fields.Integer(string='Every', required=True, default=1)
    frequency = fields.Selection([
        ('working_hour', 'Working Hours'),
        ('working_day', 'Working Days'),
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], required=True, default='month')
    anchor = fields.Selection([
        ('contract', 'Contract Start'),
        ('allocation', 'Allocation Start Date'),
        ('fixed', 'Fixed Date'),
    ], required=True, default='allocation')
    anchor_date = fields.Date(string='Fixed Anchor Date')
    accrued_gain_time = fields.Selection([
        ('start', 'At the Beginning of the Period'),
        ('end', 'At the End of the Period'),
    ], required=True, default='end')
    added_value = fields.Float(string='Allocate', digits=(16, 5), required=True, default=1)
    expiry_type = fields.Selection([
        ('never', 'Never'),
        ('delay', 'After Delay'),
        ('fixed', 'Fixed Date'),
    ], string='Expires', required=True, default='never')
    validity_count = fields.Integer(string='Valid For', required=True, default=1)
    validity_type = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], required=True, default='year')
    validity_anchor = fields.Selection([
        ('allocation', 'Allocation'),
        ('year', 'Current Year'),
    ], string='After', required=True, default='allocation')
    date_to = fields.Date(string='Valid Until')

    _frequency_count_positive = models.Constraint(
        'CHECK(frequency_count > 0)', 'The accrual frequency must be greater than zero.')
    _added_value_positive = models.Constraint(
        'CHECK(added_value > 0)', 'The accrual amount must be greater than zero.')
    _validity_count_positive = models.Constraint(
        "CHECK(expiry_type != 'delay' OR validity_count > 0)",
        'The validity duration must be greater than zero.')
    _fixed_expiry_date_required = models.Constraint(
        "CHECK(expiry_type != 'fixed' OR date_to IS NOT NULL)",
        'A validity end date is required for fixed-date expiry.')
    _fixed_anchor_date_required = models.Constraint(
        "CHECK(frequency NOT IN ('week', 'month') OR anchor != 'fixed' OR anchor_date IS NOT NULL)",
        'An anchor date is required for a fixed weekly or monthly anchor.')

    @api.constrains('work_entry_type_id', 'country_id', 'company_id')
    def _check_time_type(self):
        for rule in self:
            time_type = rule.work_entry_type_id
            if not time_type.requires_allocation or not time_type.time_off_selectable:
                raise ValidationError(self.env._('The time type must be selectable for time off and require an allocation.'))
            country = rule.country_id or rule.company_id.country_id
            if time_type.country_id and time_type.country_id != country:
                raise ValidationError(self.env._('The time type must belong to the accrual rule country.'))
            if rule.company_id.country_id and rule.country_id and rule.company_id.country_id != rule.country_id:
                raise ValidationError(self.env._('The accrual rule country must match its company country.'))

    def action_run(self):
        self.ensure_one()
        self.check_access('write')
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            raise AccessError(self.env._('Only Time Off administrators can run accrual rules.'))
        if not self.active:
            raise UserError(self.env._('Archived accrual rules cannot be run.'))
        self._check_time_type()

        companies = self.env.companies
        if self.company_id:
            companies &= self.company_id
        if self.country_id:
            companies = companies.filtered(lambda company: company.country_id == self.country_id)
        try:
            domain = Domain(literal_eval(self.employee_domain))
            domain &= Domain('active', '=', True) & Domain('company_id', 'in', companies.ids)
            employees = self.env['hr.employee'].search(domain)
        except (SyntaxError, TypeError, ValueError) as error:
            raise ValidationError(self.env._('The employee domain is invalid.')) from error

        Allocation = self.env['hr.leave.allocation']
        allocations = Allocation.search([
            ('accrual_rule_id', '=', self.id),
            ('employee_id', 'in', employees.ids),
        ])
        missing_employees = employees - allocations.employee_id
        if missing_employees:
            Allocation.with_context(allocation_skip_auto_approve=False).create([
                {
                    'employee_id': employee.id,
                    'work_entry_type_id': self.work_entry_type_id.id,
                    'accrual_rule_id': self.id,
                    'date_from': fields.Date.context_today(self),
                    'number_of_days': 0,
                }
                for employee in missing_employees
            ])
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Rule Allocations'),
            'res_model': 'hr.leave.allocation',
            'view_mode': 'list,form',
            'domain': [('accrual_rule_id', '=', self.id)],
            'context': {'create': False},
        }
