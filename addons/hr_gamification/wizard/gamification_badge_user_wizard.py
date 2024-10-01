# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class GamificationBadgeUserWizard(models.TransientModel):
    _inherit = 'gamification.badge.user.wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=False,
        compute='_compute_eployee_id', store=True)
    user_id = fields.Many2one('res.users', string='User',
        store=True, readonly=False)

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

    @api.depends('user_id')
    def _compute_employee_id(self):
        for wizard in self:
            wizard.employee_id = wizard.user_id.employee_id
