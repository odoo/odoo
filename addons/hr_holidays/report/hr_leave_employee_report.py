# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class HrLeaveEmployeeReport(models.Model):
    _name = 'hr.leave.employee.report'
    _description = 'Time Off Per Employee Summary / Report'
    _auto = False
    _order = False

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    leave_id = fields.Many2one('hr.leave', string="Time Off Request", readonly=True)
    working_schedule_aligned_date_from = fields.Datetime('Date From', readonly=True, store=True)
    number_of_days = fields.Float(readonly=True)
    number_of_hours = fields.Float(readonly=True)
    description = fields.Char()
    work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Time Type")
    state = fields.Selection([
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled'),
    ])
    color = fields.Integer(string="Color", related='work_entry_type_id.color')

    @property
    def _table_sql(self):
        # one row per day of the day_durations of the time off, computed by hr.leave._compute_day_durations;
        # the id of a row is the one of its time off and its day, so that it stays the same when the days change
        return SQL(
            """(
                SELECT hl.id::bigint * 1000000 + (leave_day.key::date - DATE '2000-01-01') AS id, hl.id AS leave_id, hl.employee_id,
                       leave_day.key::timestamp AS working_schedule_aligned_date_from,
                       (leave_day.value ->> 0)::float AS number_of_days,
                       (leave_day.value ->> 1)::float AS number_of_hours,
                       hl.private_name AS description, hl.work_entry_type_id, hl.state
                  FROM hr_leave hl
                 CROSS JOIN LATERAL jsonb_each(hl.day_durations) AS leave_day(key, value)
                 WHERE hl.employee_company_id IN %(company_ids)s
            )""",
            company_ids=tuple(self.env.companies.ids),
        )
