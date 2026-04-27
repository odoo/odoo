# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayrollStructure(models.Model):
    _name = 'hr.payroll.structure'
    _description = 'Salary Structure'

    @api.model
    def _get_default_report_id(self):
        return self.env.ref('hr_payroll.action_report_payslip', False)

    @api.model
    def _get_default_rule_ids(self):
        default_structure = self.env.ref('hr_payroll.default_structure', False)
        if not default_structure or not default_structure.rule_ids:
            return []
        vals = [
            (0, 0, {
                'name': rule.name,
                'sequence': rule.sequence,
                'code': rule.code,
                'category_id': rule.category_id,
                'condition_select': rule.condition_select,
                'condition_python': rule.condition_python,
                'amount_select': rule.amount_select,
                'amount_python_compute': rule.amount_python_compute,
                'appears_on_employee_cost_dashboard': rule.appears_on_employee_cost_dashboard,
            }) for rule in default_structure.rule_ids]
        return vals

    def _get_domain_report(self):
        if self.env.company.country_code:
            return [
                ('model', '=', 'hr.payslip'),
                ('report_type', '=', 'qweb-pdf'),
                '|',
                ('report_name', 'ilike', 'l10n_' + self.env.company.country_code.lower()),
                '&',
                ('report_name', 'ilike', 'hr_payroll'),
                ('report_name', 'not ilike', 'l10n')
            ]
        else:
            return [
                ('model', '=', 'hr.payslip'),
                ('report_type', '=', 'qweb-pdf'),
                ('report_name', 'ilike', 'hr_payroll'),
                ('report_name', 'not ilike', 'l10n')
            ]

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    type_id = fields.Many2one(
        'hr.payroll.structure.type', required=True)
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)
    note = fields.Html(string='Description')
    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id', copy=True,
        string='Salary Rules', default=_get_default_rule_ids)
    report_id = fields.Many2one('ir.actions.report',
        string="Template", domain=_get_domain_report, default=_get_default_report_id)
    payslip_name = fields.Char(string="Payslip Name", translate=True,
        help="Name to be set on a payslip. Example: 'End of the year bonus'. If not set, the default value is 'Salary Slip'")
    hide_basic_on_pdf = fields.Boolean(help="Enable this option if you don't want to display the Basic Salary on the printed pdf.")
    unpaid_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', 'hr_payroll_structure_hr_work_entry_type_rel')
    use_worked_day_lines = fields.Boolean(default=True, help="Worked days won't be computed/displayed in payslips.")
    schedule_pay = fields.Selection(related='type_id.default_schedule_pay')
    input_line_type_ids = fields.Many2many('hr.payslip.input.type', string='Other Input Line')
    ytd_computation = fields.Boolean(default=False, string='Year to Date Computation',
        help="Adds a column in the payslip that shows the accumulated amount paid for different rules during the year")

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", structure.name)) for structure, vals in zip(self, vals_list)]

    def write(self, vals):
        # Keep track of which rules are being modified
        rules = self.env['hr.salary.rule']
        # Write on rules if the country has changed values
        is_country_diff = vals.get('country_id') != self.country_id.id
        # Before the write to country_id, unlink all the salary rules' fields
        # previously generated based on the current country_id
        if 'country_id' in vals and is_country_diff:
            rules = self.rule_ids.filtered(lambda r: r.appears_on_payroll_report)
            rules.write({'appears_on_payroll_report': False})
        res = super().write(vals)
        # After the write to country_id, generate all the salary rules' fields
        # based on the new country_id
        if 'country_id' in vals and is_country_diff:
            rules.write({'appears_on_payroll_report': True})
        return res
