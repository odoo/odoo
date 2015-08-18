# -*- coding: utf-8 -*-
import datetime

from dateutil.relativedelta import relativedelta
from openerp import api, fields, models
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class hr_department(models.Model):
    _inherit = 'hr.department'

    @api.multi
    def _compute_leave_count(self):
        Holiday = self.env['hr.holidays']
        today_date = datetime.datetime.utcnow().date()
        today_start = today_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT) # get the midnight of the current utc day
        today_end = (today_date + relativedelta(hours=23, minutes=59, seconds=59)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        leave_data = Holiday.read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm'), ('type', '=', 'remove')],
            ['department_id'], ['department_id'])
        allocation_data = Holiday.read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm'), ('type', '=', 'add')],
            ['department_id'], ['department_id'])
        absence_data = Holiday.read_group(
            [('department_id', 'in', self.ids), ('state', 'not in', ['cancel', 'refuse']),
             ('date_from', '<=', today_end), ('date_to', '>=', today_start), ('type', '=', 'remove')],
            ['department_id'], ['department_id'])

        res_leave = dict((data['department_id'][0], data['department_id_count']) for data in leave_data)
        res_allocation = dict((data['department_id'][0], data['department_id_count']) for data in allocation_data)
        res_absence = dict((data['department_id'][0], data['department_id_count']) for data in absence_data)

        for department in self:
            department.leave_to_approve_count = res_leave.get(department.id, 0)
            department.allocation_to_approve_count = res_allocation.get(department.id, 0)
            department.absence_of_today = res_absence.get(department.id, 0)


    @api.multi
    def _compute_total_employee(self):
        emp_data = self.env['hr.employee'].read_group([('department_id', 'in', self.ids)], ['department_id'], ['department_id'])
        result = dict((data['department_id'][0], data['department_id_count']) for data in emp_data)
        for department in self:
            department.total_employee = result.get(department.id, 0)

    absence_of_today = fields.Integer(
        compute='_compute_leave_count', string='Absence by Today')
    leave_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Leave to Approve')
    allocation_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Allocation to Approve')
    total_employee = fields.Integer(
        compute='_compute_total_employee', string='Total Employee')
