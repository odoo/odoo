# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

MIN_SECONDS = 10  # ignore timer sessions shorter than this


class ProjectTask(models.Model):
    _inherit = 'project.task'

    timer_start = fields.Datetime(string='Cronômetro iniciado em', readonly=True, copy=False)

    @api.model
    def _timer_employee(self):
        return self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid), ('active', '=', True)], limit=1)

    def action_timer_start(self):
        self.ensure_one()
        if not self.timer_start:
            self.sudo().write({'timer_start': fields.Datetime.now()})

    def action_timer_stop(self, description=''):
        self.ensure_one()
        if not self.timer_start:
            return False
        now = fields.Datetime.now()
        elapsed_seconds = (now - self.timer_start).total_seconds()
        if elapsed_seconds < MIN_SECONDS:
            self.sudo().write({'timer_start': False})
            return False

        elapsed_hours = elapsed_seconds / 3600.0
        employee = self._timer_employee()
        if employee and self.project_id and self.env['ir.config_parameter'].sudo().get_param(
                'hr_timesheet.group_hr_timesheet_user') or True:
            self.env['account.analytic.line'].sudo().create({
                'project_id': self.project_id.id,
                'task_id': self.id,
                'employee_id': employee.id,
                'name': description.strip() if description else f'Cronômetro · {self.name}',
                'unit_amount': elapsed_hours,
                'date': fields.Date.today(),
            })
        self.sudo().write({'timer_start': False})
        return True

    def action_timer_discard(self):
        self.ensure_one()
        self.sudo().write({'timer_start': False})
