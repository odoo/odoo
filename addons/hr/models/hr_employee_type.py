from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeType(models.Model):
    _name = 'hr.employee.type'
    _description = 'Employee Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(compute='_compute_code', store=True, readonly=False)
    country_id = fields.Many2one('res.country', domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)])
    employees_count = fields.Integer(compute='_compute_employee_count', string='Employees')
    sequence = fields.Integer(default=10)

    @api.depends('name')
    def _compute_code(self):
        for contract_type in self:
            if contract_type.code:
                continue
            contract_type.code = contract_type.name

    def _compute_employee_count(self):
        employee_count_by_employee_type = dict(self.env['hr.employee']._read_group(
            domain=[
                    ('employee_type_id', 'in', self.ids),
                    ('company_id', 'in', self.env.companies.ids),
                ],
            groupby=['employee_type_id'],
            aggregates=['id:count'],
        ))
        for employee_type in self:
            employee_type.employees_count = employee_count_by_employee_type.get(employee_type, 0)

    def action_open_employees(self):
        self.ensure_one()
        employees = self.env['hr.employee'].search([
                ('employee_type_id', 'in', self.ids),
                ('company_id', 'in', self.env.companies.ids),
            ])
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

    @api.constrains('country_id')
    def _check_country_id(self):
        for record in self:
            if not record.country_id:
                continue
            countries_with_same_employee_type = self.env['hr.employee'].sudo().search_count([
                    ('employee_type_id', '=', record.id),
                    ('company_id', 'any', [('partner_id.country_code', '!=', record.country_id.code)]),
            ], limit=1)
            if countries_with_same_employee_type:
                raise ValidationError(self.env._("This employee type is used in another company, you can't modify the country where it's applicable for now.\nChange the employee type on the employees of the other company to be able to modify this."))
