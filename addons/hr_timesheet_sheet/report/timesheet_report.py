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

import tools
from osv import fields,osv

class timesheet_report(osv.osv):
    _name = "timesheet.report"
    _description = "Timesheet by month "
    _auto = False
    _columns = {
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'no_of_timesheet': fields.integer('Total Timesheet',readonly=True),
        }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'timesheet_report')
        cr.execute("""
            create or replace view timesheet_report as (
                    select
                        min(id) as id,
                        to_char(create_date, 'MM') as month,
                        user_id,
                        count(*) as no_of_timesheet
                    from
                        hr_timesheet_sheet_sheet
                    where
                         to_char(create_date,'YYYY') =  to_char(current_date,'YYYY')
                    group by
                        to_char(create_date,'MM'),user_id
            )
        """)
timesheet_report()