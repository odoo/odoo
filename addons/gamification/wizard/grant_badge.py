# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GrantBadgeWizard(models.TransientModel):
    """ Wizard allowing to grant a badge to a user"""

    _name = 'gamification.badge.user.wizard'

    user_id = fields.Many2one("res.users", string='User', required=True)
    badge_id = fields.Many2one("gamification.badge", string='Badge', required=True)
    comment = fields.Text()

    @api.multi
    def action_grant_badge(self):
        """Wizard action for sending a badge to a chosen user"""
        res = False
        for wiz in self:
            if self.env.uid == wiz.user_id.id:
                raise UserError(_('You can not grant a badge to yourself'))
            #create the badge
            values = {
                'user_id': wiz.user_id.id,
                'sender_id': self.env.uid,
                'badge_id': wiz.badge_id.id,
                'comment': wiz.comment,
            }
            res = self.env['gamification.badge.user'].create(values)._send_badge()
        return res
