# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class GamificationCurrentBadgeWizard(models.TransientModel):
    _name = 'gamification.current.badge.wizard'
    _description = 'Gamification Current Badge Wizard'

    badge_id = fields.Many2one('gamification.badge', string='Badge', required=True)
    comment = fields.Text('Comment')
    has_edit_delete_access = fields.Boolean()
    old_badge_user_id = fields.Many2one('gamification.badge.user', required=True)

    def action_update_current_badge(self):
        self.ensure_one()
        self._check_badge_access()
        self.old_badge_user_id.write({'badge_id': self.badge_id.id, 'comment': self.comment})
        return True

    def action_delete_current_badge(self):
        self.ensure_one()
        self._check_badge_access()
        self.old_badge_user_id.sudo().unlink()
        return True

    def _check_badge_access(self):
        """Check the user 'uid' can update/delete a badge and raise the appropriate exception
        if not

        Do not check for SUPERUSER_ID and the one who granted the badge
        """
        if self.env.is_admin() or self.env.uid == self.old_badge_user_id.create_uid.id:
            return

        # user level checks
        if self.env.uid == self.old_badge_user_id.user_id.id:
            raise UserError(_('You can not send a badge to yourself.'))
        elif not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(_("You Don't have access to update the badge"))

        GamificationBadge = self.env['gamification.badge']
        status_code = GamificationBadge.browse(self.old_badge_user_id.badge_id.ids)._can_grant_badge()

        # badge level checks
        if status_code == GamificationBadge.CAN_GRANT:
            return True
        elif status_code == GamificationBadge.NOBODY_CAN_GRANT:
            raise UserError(_('You cannot edit or delete this badge.'))
        elif status_code == GamificationBadge.USER_NOT_VIP:
            raise UserError(_('You cannot edit or delete this badge because you are not in the user allowed list.'))
        elif status_code == GamificationBadge.BADGE_REQUIRED:
            raise UserError(_('You cannot edit or delete this badge because you do not have the required badges.'))
        return
