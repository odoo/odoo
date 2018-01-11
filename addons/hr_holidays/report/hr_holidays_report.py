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

class hr_holidays_remaining_leaves_user(osv.osv):
    _name = "hr.holidays.remaining.leaves.user"
    _description = "Total holidays by type"
    _auto = False
    _columns = {
        'name': fields.char('Employee'),
        'no_of_leaves': fields.integer('Remaining leaves'),
        'user_id': fields.many2one('res.users', 'User'),
        'leave_type': fields.char('Leave Type'),
        }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_holidays_remaining_leaves_user')
        cr.execute("""
            CREATE or REPLACE view hr_holidays_remaining_leaves_user as (
                 SELECT
                    min(hrs.id) as id,
                    rr.name as name,
                    sum(hrs.number_of_days) as no_of_leaves,
                    rr.user_id as user_id,
                    hhs.name as leave_type
                FROM
                    hr_holidays as hrs, hr_employee as hre,
                    resource_resource as rr,hr_holidays_status as hhs
                WHERE
                    hrs.employee_id = hre.id and
                    hre.resource_id =  rr.id and
                    hhs.id = hrs.holiday_status_id
                GROUP BY
                    rr.name,rr.user_id,hhs.name
            )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
