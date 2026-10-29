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


class WorkoutPlanOption(models.Model):
    """This model workout plan option is used adding the option for the workout
    """
    _name = "workout.plan.option"
    _description = "Workout Option"
    _order = 'id'

    order_id = fields.Many2one('workout.plan', 'Workout'
                                               ' Plan Reference',
                               ondelete='cascade',
                               index=True, help="Workout plan")
    name = fields.Text('Description', required=True, help="Name")
    exercise_id = fields.Many2one('gym.exercise', 'Exercises',
                                  required=True, help="Exercise for the plan")
    equipment_ids = fields.Many2one('product.product',
                                    string='equipment', required=True,
                                    tracking=True, help="Equipment for the "
                                    "workout",
                                    domain="[('gym_product', '!=',False)]",)
    sets = fields.Integer(string="Sets", help="Set")
    repeat = fields.Integer(string="Repeat", help="Number of repeat for cycle")
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.company,
                                 help="The current company")
