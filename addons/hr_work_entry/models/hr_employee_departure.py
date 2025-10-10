# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    work_entries_warning_date = fields.Date(compute='_compute_work_entries_warning_date')

    @api.depends('do_set_date_end', 'apply_date')
    def _compute_work_entries_warning_date(self):
        validated_work_entries = dict(self.env['hr.work.entry']._read_group(
            domain=[
                ('state', '=', 'validated'),
                ('date', '>', min(dep.apply_date for dep in self if dep.apply_date)),
                ('employee_id', 'in', self.employee_id.ids),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        self.work_entries_warning_date = False
        for departure in self:
            if not departure.do_set_date_end or not validated_work_entries.get(departure.employee_id):
                continue
            future_work_entries = validated_work_entries.get(departure.employee_id)\
                .filtered(lambda we: we.date > departure.apply_date)
            if not future_work_entries:
                continue
            departure.work_entries_warning_date = max(future_work_entries.mapped('date'))

    def action_register(self):
        validated_work_entries = dict(self.env['hr.work.entry']._read_group(
            domain=[
                ('state', '=', 'validated'),
                ('date', '>', min(dep.apply_date for dep in self if dep.apply_date)),
                ('employee_id', 'in', self.employee_id.ids),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        for departure in self:
            if not departure.do_set_date_end or not validated_work_entries.get(departure.employee_id):
                continue
            future_work_entries = validated_work_entries.get(departure.employee_id)\
                .filtered(lambda we: we.date > departure.apply_date)
            if not future_work_entries:
                continue
            future_work_entries.state = 'draft'
        return super().action_register()
