# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ammu Raj (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import fields, models, tools


class DailyAttendance(models.Model):
    """Model to hold data from the biometric device"""
    _name = 'daily.attendance'
    _description = 'Daily Attendance Report'
    _auto = False
    _order = 'punching_day desc'

    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  help='Employee Name')
    punching_day = fields.Datetime(string='Date', help='Date of punching')
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help='Working address of the employee')
    attendance_type = fields.Selection([('1', 'Finger'), ('15', 'Face'),
                                        ('2', 'Type_2'), ('3', 'Password'),
                                        ('4', 'Card')], string='Category',
                                       help='Attendance detecting methods')
    punch_type = fields.Selection([('0', 'Check In'), ('1', 'Check Out'),
                                   ('2', 'Break Out'), ('3', 'Break In'),
                                   ('4', 'Overtime In'), ('5', 'Overtime Out')],
                                  string='Punching Type',
                                  help='The Punching Type of attendance')
    punching_time = fields.Datetime(string='Punching Time',
                                    help='Punching time in the device')

    def init(self):
        """Retrieve the data's for attendance report"""
        tools.drop_view_if_exists(self._cr, 'daily_attendance')
        query = """
                create or replace view daily_attendance as (
                    select
                        min(z.id) as id,
                        z.employee_id as employee_id,
                        z.write_date as punching_day,
                        z.address_id as address_id,
                        z.attendance_type as attendance_type,
                        z.punching_time as punching_time,
                        z.punch_type as punch_type
                    from zk_machine_attendance z
                        join hr_employee e on (z.employee_id=e.id)
                    GROUP BY
                        z.employee_id,
                        z.write_date,
                        z.address_id,
                        z.attendance_type,
                        z.punch_type,
                        z.punching_time
                )
            """
        self._cr.execute(query)
