# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class GamificationCurrentBadgeWizard(models.TransientModel):
    _inherit = 'gamification.badge.user'
    _name = 'gamification.current.badge.wizard'
    _description = 'Gamification Current Badge Wizard'

    old_badge_user_id = fields.Many2one('gamification.badge.user', required=True)
    has_edit_access = fields.Boolean(string='Current User Can Perform Actions')

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        ctx = self.env.context
        badge_user = self.env['gamification.badge.user'].search([('id', '=', ctx.get('active_id'))])

        defaults = {
            **defaults,
            'has_edit_access': True if self.env.user.has_group('hr.group_hr_user') or self.env.user.has_group('hr.group_hr_manager') else False,
            'old_badge_user_id': badge_user.id,
            'user_id': badge_user.user_id,
            'badge_id': badge_user.badge_id,
            'comment': badge_user.comment,
            'create_uid': badge_user.create_uid,
            'create_date': badge_user.create_date,
            'employee_id': badge_user.employee_id
        }
        return defaults

    def action_update_current_badge(self):
        self.ensure_one()
        if not (self.env.user.has_group('hr.group_hr_user') or self.env.user.has_group('hr.group_hr_manager')):
            raise UserError(_("You Don't have access to update the badge"))

        self.old_badge_user_id.badge_id = self.badge_id.id
        self.old_badge_user_id.comment = self.comment
        return True

    def action_delete_current_badge(self):
        self.ensure_one()
        if not (self.env.user.has_group('hr.group_hr_user') or self.env.user.has_group('hr.group_hr_manager')):
            raise UserError(_("You Don't have access to delete the badge"))

        self.old_badge_user_id.unlink()
        return True
