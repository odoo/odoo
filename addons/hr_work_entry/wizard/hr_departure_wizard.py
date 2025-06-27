# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    work_entries_warning_date = fields.Date(compute='_compute_work_entries_warning_date')

    def _get_future_validated_work_entries(self):
        domain = [
            ('state', '=', 'validated'),
            Domain.OR([
                ('date', '>', wiz.departure_date),
                ('employee_id', 'in', wiz.employee_ids.ids),
            ] for wiz in self),
        ]
        return dict(self.sudo().env['hr.work.entry']._read_group(
            domain=domain,
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))

    @api.depends('do_set_date_end', 'departure_date', 'employee_ids')
    def _compute_work_entries_warning_date(self):
        validated_work_entries = self._get_future_validated_work_entries()
        self.work_entries_warning_date = False
        for wizard in self:
            if not wizard.do_set_date_end:
                continue
            future_work_entries = self.env['hr.work.entry']
            for emp in wizard.employee_ids._origin:
                future_work_entries += validated_work_entries.get(emp, self.env['hr.work.entry'])
            if not future_work_entries:
                continue
            wizard.work_entries_warning_date = max(future_work_entries.mapped('date'))
