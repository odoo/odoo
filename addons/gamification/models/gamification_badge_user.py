# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class GamificationBadgeUser(models.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification User Badge'
    _inherit = ["mail.thread"]
    _order = "create_date desc"
    _rec_name = "badge_name"

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete="cascade", index=True)
    user_partner_id = fields.Many2one('res.partner', related='user_id.partner_id')
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
        body_html = self.env.ref('gamification.email_template_badge_received')._render_field('body_html', self.ids)[self.id]
        for badge_user in self:
            badge_user.message_notify(
                model=badge_user._name,
                res_id=badge_user.id,
                body=body_html,
                partner_ids=[badge_user.user_partner_id.id],
                subject=_("🎉 You've earned the %(badge)s badge!", badge=badge_user.badge_name),
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_layout',
            )

        return True

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(message, model_description, msg_vals)
        self.ensure_one()
        for group in groups:
            if group[0] == 'user':
                group[2]['has_button_access'] = False
        return groups

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.env['gamification.badge'].browse(vals['badge_id']).check_granting()
        return super().create(vals_list)

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['user_partner_id']
