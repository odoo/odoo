# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

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
        for wizard in self:
            if not wizard.do_set_date_end:
                continue
            future_work_entries = self.env['hr.work.entry']
            for emp in wizard.employee_ids:
                future_work_entries += validated_work_entries.get(emp, self.env['hr.work.entry'])
            if not future_work_entries:
                continue
            future_work_entries = future_work_entries.filtered(lambda we: we.date > wizard.apply_date)
            if not future_work_entries:
                continue
            wizard.work_entries_warning_date = max(future_work_entries.mapped('date'))
