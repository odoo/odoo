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
from odoo import fields, models, _


class WorkoutPlan(models.Model):
    """The model contain workout plan."""
    _name = "workout.plan"
    _inherit = ["mail.thread", "mail.activity.mixin", "image.mixin"]
    _description = "Workout Plan"

    name = fields.Char(string="Name")
    workout_days_ids = fields.Many2many("workout.days",
                                        string="Workout Days", help="Workout "
                                                                    "days")
    workout_plan_option_ids = fields.One2many(
        'workout.plan.option', 'order_id',
        'Optional Products Lines', help="Workout plan option")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help="The current company")

    def action_workout_plan(self):
        """Wizard opened to create my workout plans """
        assign_workout_form = self.env.ref(
            'gym_mgmt_system.view_workout_plan_wizard', False)
        assign_workout_id = self.env['assign.workout'].create({
            'workout_plan_id': self.id,
        })
        return {
            'name': _('Assign Workout Plan'),
            'type': 'ir.actions.act_window',
            'res_model': 'assign.workout',
            'res_id': assign_workout_id.id,
            'view_id': assign_workout_form,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
