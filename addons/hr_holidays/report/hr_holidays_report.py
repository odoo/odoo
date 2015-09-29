# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
