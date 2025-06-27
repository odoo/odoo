# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    work_entries_warning_date = fields.Date(compute='_compute_work_entries_warning_date')

    def _get_future_validated_work_entries(self):
        domain = Domain.AND([
            Domain('state', '=', 'validated'),
            Domain.OR([
                ('date', '>', dep.departure_date),
                ('employee_id', '=', dep.employee_id.id),
            ] for dep in self),
        ])
        return dict(self.sudo().env['hr.work.entry']._read_group(
            domain=domain,
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))

    @api.depends('do_set_date_end', 'departure_date')
    def _compute_work_entries_warning_date(self):
        validated_work_entries_sudo = self._get_future_validated_work_entries()
        self.work_entries_warning_date = False
        for departure in self:
            future_work_entries = validated_work_entries_sudo.get(departure.employee_id)
            if not departure.do_set_date_end or not future_work_entries:
                continue
            departure.work_entries_warning_date = max(future_work_entries.mapped('date'))

    def action_register(self):
        validated_work_entries_sudo = self._get_future_validated_work_entries()
        we_to_draft = self.env['hr.work.entry']
        for departure in self:
            future_work_entries = validated_work_entries_sudo.get(departure.employee_id)
            if departure.do_set_date_end and future_work_entries:
                we_to_draft += future_work_entries
        we_to_draft.with_context({'departure_unlink': True}).write({'state': 'draft'})
        return super().action_register()
