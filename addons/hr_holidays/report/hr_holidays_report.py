# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models
from openerp import tools


class HrHolidaysRemainingLeavesUser(models.Model):
    _name = "hr.holidays.remaining.leaves.user"
    _description = "Total holidays by type"
    _auto = False

    name = fields.Char(string='Employee')
    no_of_leaves = fields.Integer(string='Remaining leaves')
    user_id = fields.Many2one(comodel_name='res.users', string='User')
    leave_type = fields.Char(string='Leave Type')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_holidays_remaining_leaves_user')
        cr.execute("""
            CREATE OR REPLACE VIEW hr_holidays_remaining_leaves_user AS (
                 SELECT
                    min(hrs.id) AS id,
                    rr.name AS name,
                    sum(hrs.number_of_days) AS no_of_leaves,
                    rr.user_id AS user_id,
                    hhs.name AS leave_type
                FROM
                    hr_holidays AS hrs, hr_employee AS hre,
                    resource_resource AS rr,hr_holidays_status AS hhs
                WHERE
                    hrs.employee_id = hre.id and
                    hre.resource_id =  rr.id and
                    hhs.id = hrs.holiday_status_id
                GROUP BY
                    rr.name,rr.user_id,hhs.name
            )
        """)
