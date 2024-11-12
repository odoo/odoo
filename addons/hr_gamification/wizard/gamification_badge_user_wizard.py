# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class GamificationBadgeUserWizard(models.TransientModel):
    _inherit = 'gamification.badge.user.wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=False)
    user_id = fields.Many2one('res.users', string='User', compute='_compute_user_id',
        store=True, readonly=False, compute_sudo=True)

    def action_grant_badge(self):
        """Wizard action for sending a badge to a chosen employee"""
        if self.env.uid == self.user_id.id:
            raise UserError(_('You can not send a badge to yourself.'))
        values = {
            'user_id': self.user_id.id,
            'sender_id': self.env.uid,
            'badge_id': self.badge_id.id,
            'employee_id': self.employee_id.id,
            'comment': self.comment,
        }

        return self.env['gamification.badge.user'].create(values)._send_badge()

    @api.depends('employee_id')
    def _compute_user_id(self):
        for wizard in self:
            wizard.user_id = wizard.employee_id.user_id
