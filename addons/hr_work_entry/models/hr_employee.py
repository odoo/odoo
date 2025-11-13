# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.tools import SQL


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    has_work_entries = fields.Boolean(compute='_compute_has_work_entries', groups="base.group_system,hr.group_hr_user")
    work_entry_source = fields.Selection(readonly=False, related="version_id.work_entry_source", inherited=True, groups="hr.group_hr_manager")
    work_entry_source_calendar_invalid = fields.Boolean(related="version_id.work_entry_source_calendar_invalid", inherited=True, groups="hr.group_hr_manager")

    def _compute_has_work_entries(self):
        if self.ids:
            result = dict(self.env.execute_query(SQL(
                """ SELECT id, EXISTS(SELECT 1 FROM hr_work_entry WHERE employee_id = e.id LIMIT 1)
                      FROM hr_employee e
                     WHERE id in %s """,
                tuple(self.ids),
            )))
        else:
            result = {}

        for employee in self:
            employee.has_work_entries = result.get(employee._origin.id, False)

    def create_version(self, values):
        new_version = super().create_version(values)
        new_version.update({
            'date_generated_from': fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            'date_generated_to': fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        })
        return new_version

    def action_open_work_entries(self, initial_date=False):
        self.ensure_one()
        ctx = {'default_employee_id': self.id}
        if initial_date:
            ctx['initial_date'] = initial_date
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s work entries', self.display_name),
            'view_mode': 'calendar,list,form',
            'res_model': 'hr.work.entry',
            'path': 'work-entries',
            'context': ctx,
            'domain': [('employee_id', '=', self.id)],
        }

    def generate_work_entries(self, date_start, date_stop, force=False):
        date_start = fields.Date.to_date(date_start)
        date_stop = fields.Date.to_date(date_stop)

        if self:
            versions = self._get_versions_with_contract_overlap_with_period(date_start, date_stop)
        else:
            versions = self._get_all_versions_with_contract_overlap_with_period(date_start, date_stop)
        return versions.generate_work_entries(date_start, date_stop, force=force)
