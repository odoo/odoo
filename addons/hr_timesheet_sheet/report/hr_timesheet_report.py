# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import tools
from openerp.osv import fields,osv

class hr_timesheet_report(osv.osv):
    _inherit = "hr.timesheet.report"
    _columns = {
        'nbr': fields.integer('# Nbr Timesheet',readonly=True),
        'total_diff': fields.float('# Total Diff',readonly=True),
        'total_timesheet': fields.float('# Total Timesheet',readonly=True),
        'total_attendance': fields.float('# Total Attendance',readonly=True),
        'department_id':fields.many2one('hr.department','Department',readonly=True),
        'date_from': fields.date('Date from',readonly=True,),
        'date_to': fields.date('Date to',readonly=True),
        'state' : fields.selection([
            ('new', 'New'),
            ('draft','Draft'),
            ('confirm','Confirmed'),
            ('done','Done')], 'Status', readonly=True),
        }

    def _select(self):
        return """
        WITH
            totals AS (
                SELECT
                    d.sheet_id,
                    d.name as date,
                    sum(total_difference) / coalesce(sum(j.count),1) as total_diff,
                    sum(total_timesheet) / coalesce(sum(j.count),1) as total_timesheet,
                    sum(total_attendance) / coalesce(sum(j.count),1) as total_attendance
                FROM hr_timesheet_sheet_sheet_day d left join (
                    SELECT
                        a.sheet_id,
                        a.date,
                        count(*)
                    FROM account_analytic_line a
                    GROUP BY a.sheet_id, a.date
                ) j ON (d.sheet_id = j.sheet_id AND d.name = j.date)
                GROUP BY d.sheet_id, d.name
            )
        """ + super(hr_timesheet_report, self)._select() + """,
                        htss.name,
                        htss.date_from,
                        htss.date_to,
                        count(*) as nbr,
                        sum(t.total_diff) as total_diff,
                        sum(t.total_timesheet) as total_timesheet,
                        sum(t.total_attendance) as total_attendance,
                        htss.department_id,
                        htss.state"""

    def _from(self):
        return super(hr_timesheet_report, self)._from() + "left join hr_timesheet_sheet_sheet as htss ON (aal.sheet_id=htss.id) left join totals as t on (t.sheet_id = aal.sheet_id and t.date = aal.date)"

    def _group_by(self):
        return super(hr_timesheet_report, self)._group_by() + """,
                        htss.date_from,
                        htss.date_to,
                        aal.unit_amount,
                        aal.amount,
                        htss.name,
                        htss.state,
                        htss.id,
                        htss.department_id"""
