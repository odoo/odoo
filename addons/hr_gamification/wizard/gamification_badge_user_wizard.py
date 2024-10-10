# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class GamificationBadgeUserWizard(models.TransientModel):
    _inherit = 'gamification.badge.user.wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=False)
    user_id = fields.Many2one('res.users', string='User', compute='_compute_user_id',
        store=True, readonly=False, compute_sudo=True)

    @api.depends('employee_id')
    def _compute_user_id(self):
        for wizard in self:
            wizard.user_id = wizard.employee_id.user_id
