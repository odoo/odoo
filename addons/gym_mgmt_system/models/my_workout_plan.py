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


class MyWorkoutPlan(models.Model):
    """This model for showing my workout plans."""
    _name = "my.workout.plan"
    _inherit = ["mail.thread", "mail.activity.mixin", "image.mixin"]
    _description = "My Workout Plan"
    _rec_name = "payment_term_id"

    payment_term_id = fields.Many2one('workout.plan',
                                      string="Name", help="payment term ")
    assign_to_id = fields.Many2one('res.partner',
                                   string='Assign To',
                                   domain="[('gym_member', '!=',False)]",
                                   default=lambda self: self.env.user,
                                   help="Assigned person")
    from_date = fields.Date(string='Date From', help="Start date")
    to_date = fields.Date(string='Date To', help="End date")
