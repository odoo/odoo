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
        template = self.env.ref('gamification.email_template_badge_received')

        for badge_user in self:
            self.env['mail.thread'].message_post_with_template(
                template.id,
                model=badge_user._name,
                res_id=badge_user.id,
                composition_mode='mass_mail',
                # `website_forum` triggers `_cron_update` which triggers this method for template `Received Badge`
                # for which `badge_user.user_id.partner_id.ids` equals `[8]`, which is then passed to  `self.env['mail.compose.message'].create(...)`
                # which expects a command list and not a list of ids. In master, this wasn't doing anything, at the end composer.partner_ids was [] and not [8]
                # I believe this line is useless, it will take the partners to which the template must be send from the template itself (`partner_to`)
                # The below line was therefore pointless.
                # partner_ids=badge_user.user_id.partner_id.ids,
            )

        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.env['gamification.badge'].browse(vals['badge_id']).check_granting()
        return super().create(vals_list)
