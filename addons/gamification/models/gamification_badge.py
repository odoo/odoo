# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GamificationBadgeUser(models.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification user badge'
    _order = "create_date desc"
    _rec_name = "badge_name"

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete="cascade")
    sender_id = fields.Many2one('res.users', string="Sender", help="The user who has send the badge")
    badge_id = fields.Many2one('gamification.badge', string='Badge', required=True, ondelete="cascade")
    challenge_id = fields.Many2one('gamification.challenge', string='Challenge originating', help="If this badge was rewarded through a challenge")
    comment = fields.Text()
    badge_name = fields.Char(related='badge_id.name')

    @api.model
    def create(self, vals):
        self.env['gamification.badge'].browse(vals.get('badge_id')).check_granting()
        return super(GamificationBadgeUser, self).create(vals)

    @api.multi
    def _send_badge(self):
        """Send a notification to a user for receiving a badge

        Does not verify constrains on badge granting.
        The users are added to the owner_ids (create badge_user if needed)
        The stats counters are incremented
        :param ids: list(int) of badge users that will receive the badge
        """
        res = True
        MailTemplate = self.env['mail.template']
        badge_template = self.env.ref('gamification.email_template_badge_received')
        for badge_user in self:
            template = badge_template.get_email_template(badge_user.id)
            body_html = MailTemplate.with_context(template._context).render_template(template.body_html, 'gamification.badge.user', badge_user.id)
            res = badge_user.user_id.message_post(
                body=body_html,
                subtype='gamification.mt_badge_granted',
                partner_ids=badge_user.user_id.partner_id.ids)
        return res


class GamificationBadge(models.Model):
    """Badge object that users can send and receive"""

    CAN_GRANT = 1
    NOBODY_CAN_GRANT = 2
    USER_NOT_VIP = 3
    BADGE_REQUIRED = 4
    TOO_MANY = 5

    _name = 'gamification.badge'
    _description = 'Gamification badge'
    _inherit = 'mail.thread'

    name = fields.Char(string='Badge', required=True, translate=True)
    description = fields.Text(translate=True)
    image = fields.Binary(attachment=True, help="This field holds the image used for the badge, limited to 256x256")
    rule_auth = fields.Selection([
        ('everyone', 'Everyone'),
        ('users', 'A selected list of users'),
        ('having', 'People having some badges'),
        ('nobody', 'No one, assigned through challenges')],
        string="Allowance to Grant",
        help="Who can grant this badge",
        required=True, default='everyone')
    rule_auth_user_ids = fields.Many2many(
        'res.users', 'rel_badge_auth_users',
        string='Authorized Users',
        help="Only these people can give this badge")
    rule_auth_badge_ids = fields.Many2many(
        'gamification.badge', 'gamification_badge_rule_badge_rel', 'badge1_id', 'badge2_id',
        string='Required Badges',
        help="Only the people having these badges can give this badge")

    rule_max = fields.Boolean(
        string='Monthly Limited Sending', help="Check to set a monthly limit per person of sending this badge")
    rule_max_number = fields.Integer(
        string='Limitation Number', help="The maximum number of time this badge can be sent per month per person.")
    stat_my_monthly_sending = fields.Integer(
        compute='_compute_badge_user_stats',
        string='My Monthly Sending Total', help="The number of time the current user has sent this badge this month.")
    remaining_sending = fields.Integer(
        compute='_compute_remaining_sending',
        string='Remaining Sending Allowed', help="If a maxium is set")

    challenge_ids = fields.One2many(
        'gamification.challenge', 'reward_id',
        string="Reward of Challenges")

    goal_definition_ids = fields.Many2many(
        'gamification.goal.definition', 'badge_unlocked_definition_rel',
        string='Rewarded by',
        help="The users that have succeeded theses goals will receive automatically the badge.")

    owner_ids = fields.One2many(
        'gamification.badge.user', 'badge_id',
        string='Owners', help='The list of instances of this badge granted to users')
    active = fields.Boolean(default=True)
    unique_owner_ids = fields.Many2many(
        'res.users', compute='_compute_owners_info',
        string='Unique Owners',
        help="The list of unique users having received this badge.")

    stat_count = fields.Integer(
        compute='_compute_owners_info', string='Total',
        help="The number of time this badge has been received.")
    stat_count_distinct = fields.Integer(
        compute='_compute_owners_info',
        string='Number of users', help="The number of time this badge has been received by unique users.")
    stat_this_month = fields.Integer(
        compute='_compute_badge_user_stats',
        string='Monthly total', help="The number of time this badge has been received this month.")
    stat_my = fields.Integer(
        compute='_compute_badge_user_stats', string='My Total',
        help="The number of time the current user has received this badge.")
    stat_my_this_month = fields.Integer(
        compute='_compute_badge_user_stats',
        string='My Monthly Total', help="The number of time the current user has received this badge this month.")

    def _compute_badge_user_stats(self):
        """Return stats related to badge users"""
        BadgeUser = self.env['gamification.badge.user']
        today = fields.Date.from_string(fields.Date.today())
        first_month_day = fields.Date.to_string(today.replace(day=1))
        for badge in self:
            badge_users = BadgeUser.search([('badge_id', '=', badge.id)])
            badge.stat_my = len(badge_users.filtered(lambda x: x.user_id.id == self.env.uid))
            badge.stat_this_month = len(badge_users.filtered(lambda x: x.create_date >= first_month_day))
            badge.stat_my_this_month = len(badge_users.filtered(lambda x: x.user_id.id == self.env.uid and x.create_date >= first_month_day))
            badge.stat_my_monthly_sending = len(badge_users.filtered(lambda x: x.create_uid.id == self.env.uid and x.create_date >= first_month_day))

    def _compute_remaining_sending(self):
        """Computes the number of badges remaining the user can send

        0 if not allowed or no remaining
        integer if limited sending
        -1 if infinite (should not be displayed)
        """
        for badge in self:
            if badge._can_grant_badge() != 1:
                # if the user cannot grant this badge at all, result is 0
                badge.remaining_sending = 0
            elif not badge.rule_max:
                # if there is no limitation, -1 is returned which means 'infinite'
                badge.remaining_sending = -1
            else:
                badge.remaining_sending = badge.rule_max_number - badge.stat_my_monthly_sending

    def _compute_owners_info(self):
        """Return:
            the list of unique res.users ids having received this badge
            the total number of time this badge was granted
            the total number of users this badge was granted to
        """
        for bid in self:
            bid.stat_count = 0
            bid.stat_count_distinct = 0
            bid.unique_owner_ids = []

        self.env.cr.execute("""
            SELECT badge_id, count(user_id) as stat_count,
                count(distinct(user_id)) as stat_count_distinct,
                array_agg(distinct(user_id)) as unique_owner_ids
            FROM gamification_badge_user
            WHERE badge_id in %s
            GROUP BY badge_id
            """, (tuple(self.ids),))
        for (badge_id, stat_count, stat_count_distinct, unique_owner_ids) in self.env.cr.fetchall():
            badge = self.browse(badge_id)
            badge.stat_count = stat_count
            badge.stat_count_distinct = stat_count_distinct
            badge.unique_owner_ids = unique_owner_ids

    def check_granting(self):
        """Check the user 'uid' can grant the badge 'badge_id' and raise the appropriate exception
        if not

        Do not check for SUPERUSER_ID
        """
        status_code = self._can_grant_badge()
        if status_code == self.CAN_GRANT:
            return True
        elif status_code == self.NOBODY_CAN_GRANT:
            raise UserError(_('This badge can not be sent by users.'))
        elif status_code == self.USER_NOT_VIP:
            raise UserError(_('You are not in the user allowed list.'))
        elif status_code == self.BADGE_REQUIRED:
            raise UserError(_('You do not have the required badges.'))
        elif status_code == self.TOO_MANY:
            raise UserError(_('You have already sent this badge too many time this month.'))
        else:
            _logger.exception("Unknown badge status code: %d" % int(status_code))
        return False

    def _can_grant_badge(self):
        """Check if a user can grant a badge to another user

        :param uid: the id of the res.users trying to send the badge
        :param badge_id: the granted badge id
        :return: integer representing the permission.
        """
        if self.env.uid == SUPERUSER_ID:
            return self.CAN_GRANT

        if self.rule_auth == 'nobody':
            return self.NOBODY_CAN_GRANT

        elif self.rule_auth == 'users' and self.env.uid not in self.rule_auth_user_ids.ids:
            return self.USER_NOT_VIP

        elif self.rule_auth == 'having':
            all_user_badges = self.env['gamification.badge.user'].search([('user_id', '=', self.env.uid)]).mapped('badge_id')
            for required_badge in self.rule_auth_badge_ids:
                if required_badge.id not in all_user_badges.ids:
                    return self.BADGE_REQUIRED

        if self.rule_max and self.stat_my_monthly_sending >= self.rule_max_number:
            return self.TOO_MANY

        # badge.rule_auth == 'everyone' -> no check
        return self.CAN_GRANT

    def check_progress(self, cr, uid, context=None):
        try:
            model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'gamification', 'badge_hidden')
        except ValueError:
            return True
        badge_user_obj = self.pool.get('gamification.badge.user')
        if not badge_user_obj.search(cr, uid, [('user_id', '=', uid), ('badge_id', '=', res_id)], context=context):
            values = {
                'user_id': uid,
                'badge_id': res_id,
            }
            badge_user_obj.create(cr, SUPERUSER_ID, values, context=context)
        return True
