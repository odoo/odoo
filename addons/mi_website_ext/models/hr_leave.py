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
        if self.env.context.get('bypass_remunerated_check'):
            return
       
        if self.env.user.id == 6:
            return 

        if is_write and self.create_uid.id == 6:
            return    

        leave_type_id = vals.get('holiday_status_id') or (self.holiday_status_id.id if is_write else False)
        if not leave_type_id:
            return
        leave_type = self.env['hr.leave.type'].browse(leave_type_id)

        if not leave_type or leave_type.name != 'Solicitud de permiso':
            return 

        employee_id = vals.get('employee_id') or (self.employee_id.id if is_write else False)
        if not employee_id:
            return
        employee = self.env['hr.employee'].browse(employee_id)

        request_date_from_str = vals.get('request_date_from') or (fields.Date.to_string(self.request_date_from) if is_write else None)
        if not request_date_from_str:
            return 

        request_date = fields.Date.to_date(request_date_from_str)
        
        requested_hours = 0.0
        if 'number_of_hours' in vals:
            requested_hours = vals.get('number_of_hours', 0.0)
        elif is_write and 'number_of_hours' not in vals:
            requested_hours = self.number_of_hours
        elif 'number_of_days' in vals:
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            requested_hours = vals.get('number_of_days', 0.0) * hours_per_day

        month_start = request_date.replace(day=1)
        month_end = month_start + relativedelta(months=1, days=-1)

        domain = [
            ('employee_id', '=', employee_id),
            ('holiday_status_id', '=', leave_type_id),
            ('state', '=', 'validate'), 
            ('request_date_from', '>=', month_start),
            ('request_date_from', '<=', month_end),
        ]
        if is_write:
            domain.append(('id', '!=', self.id))

        approved_leaves = self.env['hr.leave'].search(domain)
        used_hours = sum(approved_leaves.mapped('number_of_hours'))

        monthly_limit = 8.0
        if used_hours + requested_hours > monthly_limit:
            raise ValidationError(_("Usted ha utilizado el límite mensual de horas de permiso permitidas.")) 

    def action_force_cancel(self):
        self.with_context(bypass_remunerated_check=True).sudo().write({'state': 'cancel'})
        return True