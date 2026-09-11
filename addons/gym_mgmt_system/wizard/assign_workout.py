# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sahla Sherin (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class AssignWorkout(models.TransientModel):
    """The model is for workout plan."""
    _name = 'assign.workout'
    _description = 'Assign Workout'

    assign_to_id = fields.Many2one('res.partner',
                                   string='Assign To',
                                   domain="[('gym_member', '!=',False)]",
                                   help="To mention the assign")
    workout_plan_id = fields.Many2one('workout.plan',
                                      string='Workout Plan', required=True,
                                      readonly=True, help="Add workout plan")
    from_date = fields.Date(string='Date From', help="From date")
    to_date = fields.Date(string='Date To', help="To date")

    def action_workout(self):
        """ create my workout plan of assign members only"""
        record = self.env['my.workout.plan'].create({
            'payment_term_id': self.workout_plan_id.id,
            'assign_to_id': self.assign_to_id.id,
            'from_date': self.from_date,
            'to_date': self.to_date,
        })
        return record
