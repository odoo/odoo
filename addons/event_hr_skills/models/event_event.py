# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class EventEvent(models.Model):
    _inherit = ['event.event']
    is_active_employee_registered = fields.Boolean(store=False, search='_search_is_active_employee_registered')

    def _search_is_active_employee_registered(self, operator, value):
        assert value in [True, False], "Searched value must be boolean"
        assert operator in ['=', '!='], "Operator not supported"

        if employee_id := self.env.context.get('active_employee_id'):
            domain = [
                ('registration_ids', 'any', [
                    ('partner_id.employee_ids', 'any', [('id', '=', employee_id)]),
                    ('state', 'in', ['open', 'done'])
                ])
            ]
        else:
            domain = expression.FALSE_LEAF

        negate = value != (operator == '=')
        return ['!', *domain] if negate else domain

    def action_register_employee(self):
        employee = self.env['hr.employee'].browse(self.env.context.get('active_employee_id'))
        if not employee or not employee.work_contact_id:
            return

        self.env['hr.resume.line'].create([
            event._get_resume_line_vals(employee)
            for event in self
        ])

    def _get_resume_line_vals(self, employee):
        self.ensure_one()
        return {
            'employee_id': employee.id,
            'name': self.name,
            'event_id': self.id,
            'date_start': self.date_begin,
            'date_end': self.date_end,
            'description': 'Attended ' + self.name,
            'line_type_id': self.env['hr.resume.line'].get_event_type_id(),
        }

