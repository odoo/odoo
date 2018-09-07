# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class GamificationBadgeUserWizard(models.TransientModel):
    _inherit = 'gamification.badge.user.wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    user_id = fields.Many2one('res.users', string='User',
        related='employee_id.user_id', store=True, readonly=True)

    # TODO 12.0/master remove this hack by changing the model
    @api.model
    def create(self, values):
        employee = self.env['hr.employee'].browse(values['employee_id'])
        values['user_id'] = employee.user_id.id
        try:
            return super(GamificationBadgeUserWizard, self).create(values)
        except AccessError:
            # an employee can not write on another employee
            # force sudo because of related
            return super(GamificationBadgeUserWizard, self.sudo()).create(values)

    @api.multi
    def action_grant_badge(self):
        """Wizard action for sending a badge to a chosen employee"""
        if not self.user_id:
            raise UserError(_('You can send badges only to employees linked to a user.'))

        if self.env.uid == self.user_id.id:
            raise UserError(_('You can not send a badge to yourself'))

        values = {
            'user_id': self.user_id.id,
            'sender_id': self.env.uid,
            'badge_id': self.badge_id.id,
            'employee_id': self.employee_id.id,
            'comment': self.comment,
        }

        return self.env['gamification.badge.user'].create(values)._send_badge()
