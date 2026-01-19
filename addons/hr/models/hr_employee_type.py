from odoo import api, fields, models


class HrEmployeeType(models.Model):
    _name = 'hr.employee.type'
    _description = 'Employee Type'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(compute='_compute_code', store=True, readonly=False)
    country_id = fields.Many2one('res.country', domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)])
    employees_count = fields.Integer(compute='_compute_employee_count', string='Employees')

    @api.depends('name')
    def _compute_code(self):
        for contract_type in self:
            if contract_type.code:
                continue
            contract_type.code = contract_type.name

    def _compute_employee_count(self):
        employee_count_by_employee_type = dict(self.env['hr.employee']._read_group(
            domain=[('employee_type_id', 'in', self.ids)],
            groupby=['employee_type_id'],
            aggregates=['id:count'],
        ))
        for employee_type in self:
            employee_type.employees_count = employee_count_by_employee_type.get(employee_type, 0)

    def action_open_employees(self):
        self.ensure_one()
        employees = self.env['hr.employee'].search([('employee_type_id', 'in', self.ids)])
        if len(employees) == 1:
            return {
                'name': self.env._('Employee'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee',
                'res_id': employees.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            }
        return {
            'name': self.env._('Related Employees'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'kanban, form',
            'views': [(False, 'kanban'), (False, 'form')],
            'domain': [('id', 'in', employees.ids)],
        }
