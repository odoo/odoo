#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from . import models
from . import wizard


def _generate_attendances(env):
    hne_contract = env.ref('hr_work_entry_contract_attendance.hr_contract_hne', raise_if_not_found=False)
    if not hne_contract or env['hr.attendance'].sudo().search_count([('employee_id', '=', hne_contract.employee_id.id)]):
        return
    employee = hne_contract.employee_id
    #generate attendances for ngh for every day up until last week (those will be hardcoded with weird hours)
    today = datetime.today()
    delta = (today + relativedelta(weeks=-1, days=-today.weekday(), weekday=0)).date() - hne_contract.date_start
    attendance_create_vals = []
    for i in range(delta.days):
        day = hne_contract.date_start + timedelta(days=i)
        #not on weekend days
        if day.weekday() >= 5:
            continue
        attendance_create_vals.extend([
            {
                'employee_id': employee.id,
                'check_in': day.strftime('%Y-%m-%d 08:00:00'),
                'check_out': day.strftime('%Y-%m-%d 12:00:00'),
            },
            {
                'employee_id': employee.id,
                'check_in': day.strftime('%Y-%m-%d 13:00:00'),
                'check_out': day.strftime('%Y-%m-%d 17:00:00'),
            }
        ])
    attendance_create_vals.extend([
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=0)).strftime('%Y-%m-%d 08:00:00'),
            "check_out": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=0)).strftime('%Y-%m-%d 12:00:00'),
        },
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=0)).strftime('%Y-%m-%d 13:00:00'),
            "check_out": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=0)).strftime('%Y-%m-%d 18:00:00'),
        },
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=1)).strftime('%Y-%m-%d 07:00:00'),
            "check_out": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=1)).strftime('%Y-%m-%d 11:00:00'),
        },
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=1)).strftime('%Y-%m-%d 14:00:00'),
            "check_out": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=1)).strftime('%Y-%m-%d 19:00:00'),
        },
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=2)).strftime('%Y-%m-%d 08:00:00'),
            "check_out": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=2)).strftime('%Y-%m-%d 15:00:00'),
        },
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=2)).strftime('%Y-%m-%d 16:00:00'),
            "check_out": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=2)).strftime('%Y-%m-%d 18:00:00'),
        },
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=3)).strftime('%Y-%m-%d 02:00:00'),
            "check_out": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=3)).strftime('%Y-%m-%d 10:00:00'),
        },
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=4)).strftime('%Y-%m-%d 10:00:00'),
            "check_out": (today+relativedelta(weeks=-1, days=-today.weekday(), weekday=4)).strftime('%Y-%m-%d 14:00:00'),
        },
        {
            "employee_id": employee.id,
            "check_in": (today+relativedelta(weeks=-1, weekday=4)).strftime('%Y-%m-%d 15:00:00'),
            "check_out": (today+relativedelta(weeks=-1, weekday=4)).strftime('%Y-%m-%d 19:00:00'),
        }
    ])
    env['hr.attendance'].create(attendance_create_vals)
