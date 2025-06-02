from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_remunerated_permission_limit(vals)
        return super().create(vals_list)

    def write(self, vals):
        for record in self:
            record._check_remunerated_permission_limit(vals, is_write=True)
        return super().write(vals)

    def _check_remunerated_permission_limit(self, vals, is_write=False):
        # Verifica que sea 'Solicitud de permiso'
        leave_type_id = vals.get('holiday_status_id') or (self.holiday_status_id.id if is_write else False)
        leave_type = self.env['hr.leave.type'].browse(leave_type_id)

        if not leave_type or leave_type.name != 'Solicitud de permiso':
            return  # No validamos otros tipos

        # Obtener empleado
        employee_id = vals.get('employee_id') or (self.employee_id.id if is_write else False)
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee:
            return

        # Fechas
        date_from = fields.Date.to_date(vals.get('request_date_from')) if vals.get('request_date_from') else self.request_date_from
        date_to = fields.Date.to_date(vals.get('request_date_to')) if vals.get('request_date_to') else self.request_date_to
        if not date_from or not date_to:
            return

        # Calcular horas solicitadas
        requested_hours = 0.0
        if vals.get('request_unit') == 'hour' or (not vals.get('request_unit') and self.request_unit == 'hour'):
            requested_hours = vals.get('number_of_hours_display') or self.number_of_hours_display
        elif vals.get('number_of_days'):
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            requested_hours = vals['number_of_days'] * hours_per_day
        else:
            duration = vals.get('duration_display', self.duration_display or '')
            if 'hour' in duration.lower():
                parts = duration.split(' ')[0].split(':')
                if len(parts) == 2:
                    requested_hours = float(parts[0]) + float(parts[1]) / 60.0
                elif len(parts) == 1:
                    requested_hours = float(parts[0])

        # Consultar horas disponibles para el mes
        available_hours = self.env.user.get_available_permission_hours(employee, date_from, date_to)

        if requested_hours > available_hours:
            raise ValidationError(_(
                "No puedes solicitar %.1f horas. Solo tienes %.1f horas disponibles para el mes de la solicitud."
            ) % (requested_hours, available_hours))