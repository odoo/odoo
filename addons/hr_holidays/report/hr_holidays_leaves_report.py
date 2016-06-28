# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class HrHolidaysRemainingLeavesUser(models.Model):

    _name = "hr.holidays.remaining.leaves.user"
    _description = "Total holidays by type"
    _auto = False

    name = fields.Char('Employee', readonly=True)
    no_of_leaves = fields.Integer('Remaining leaves', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    leave_type = fields.Char('Leave Type', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_holidays_remaining_leaves_user')
        self._cr.execute("""
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
