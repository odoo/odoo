# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class GamificationGoalWizard(models.TransientModel):
    """Wizard to update a manual goal"""
    _name = 'gamification.goal.wizard'
    _description = 'Gamification Goal Wizard'

    goal_id = fields.Many2one("gamification.goal", string='Goal', required=True)
    current = fields.Float('Current')

    def action_update_current(self):
        """Wizard action for updating the current value"""
        for wiz in self:
            wiz.goal_id.write({
                'current': wiz.current,
                'goal_id': wiz.goal_id.id,
                'to_update': False,
            })
            wiz.goal_id.update_goal()

        return False
