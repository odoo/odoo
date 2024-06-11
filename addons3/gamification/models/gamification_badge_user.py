# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BadgeUser(models.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification User Badge'
    _order = "create_date desc"
    _rec_name = "badge_name"

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete="cascade", index=True)
    sender_id = fields.Many2one('res.users', string="Sender")
    badge_id = fields.Many2one('gamification.badge', string='Badge', required=True, ondelete="cascade", index=True)
    challenge_id = fields.Many2one('gamification.challenge', string='Challenge')
    comment = fields.Text('Comment')
    badge_name = fields.Char(related='badge_id.name', string="Badge Name", readonly=False)
    level = fields.Selection(
        string='Badge Level', related="badge_id.level", store=True, readonly=True)

    def _send_badge(self):
        """Send a notification to a user for receiving a badge

        Does not verify constrains on badge granting.
        The users are added to the owner_ids (create badge_user if needed)
        The stats counters are incremented
        :param ids: list(int) of badge users that will receive the badge
        """
        template = self.env.ref(
            'gamification.email_template_badge_received',
            raise_if_not_found=False
        )
        if not template:
            return

        for badge_user in self:
            template.send_mail(
                badge_user.id,
            )

        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.env['gamification.badge'].browse(vals['badge_id']).check_granting()
        return super().create(vals_list)
