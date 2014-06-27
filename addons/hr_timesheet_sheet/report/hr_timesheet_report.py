# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.osv import fields,osv

class hr_timesheet_report(osv.osv):
    _inherit = "hr.timesheet.report"
    _columns = {
        'to_invoice': fields.many2one('hr_timesheet_invoice.factor', 'Type of Invoicing',readonly=True),
        'nbr': fields.integer('#Nbr',readonly=True),
        'total_diff': fields.float('#Total Diff',readonly=True),
        'total_timesheet': fields.float('#Total Timesheet',readonly=True),
        'total_attendance': fields.float('#Total Attendance',readonly=True),
        'department_id':fields.many2one('hr.department','Department',readonly=True),
        'date_from': fields.date('Date from',readonly=True,),
        'date_to': fields.date('Date to',readonly=True),
        'date_current': fields.date('Current date', required=True),
        'state' : fields.selection([
            ('new', 'New'),
            ('draft','Draft'),
            ('confirm','Confirmed'),
            ('done','Done')], 'Status', readonly=True),
        }

    def _select(self):
        return super(hr_timesheet_report, self)._select() + """,
                        htss.name,
                        htss.date_from,
                        htss.date_to,
                        count(*) as nbr,
                        (SELECT   sum(day.total_difference)
                            FROM hr_timesheet_sheet_sheet AS sheet 
                            LEFT JOIN hr_timesheet_sheet_sheet_day AS day 
                            ON (sheet.id = day.sheet_id) where sheet.id=htss.id) as total_diff,
                        (SELECT sum(day.total_timesheet)
                            FROM hr_timesheet_sheet_sheet AS sheet 
                            LEFT JOIN hr_timesheet_sheet_sheet_day AS day 
                            ON (sheet.id = day.sheet_id) where sheet.id=htss.id) as total_timesheet,
                        (SELECT sum(day.total_attendance)
                            FROM hr_timesheet_sheet_sheet AS sheet 
                            LEFT JOIN hr_timesheet_sheet_sheet_day AS day 
                            ON (sheet.id = day.sheet_id) where sheet.id=htss.id) as total_attendance,
                        aal.to_invoice,
                        htss.department_id,
                        htss.state"""

    def _from(self):
        return super(hr_timesheet_report, self)._from() + "left join hr_timesheet_sheet_sheet as htss ON (hat.sheet_id=htss.id)"

    def _group_by(self):
        return super(hr_timesheet_report, self)._group_by() + """,
                        htss.date_from,
                        htss.date_to,
                        aal.unit_amount,
                        aal.amount,
                        aal.to_invoice,
                        htss.name,
                        htss.state,
                        htss.id,
                        htss.department_id"""


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
