# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import date

from odoo import api, fields, models, _, exceptions

_logger = logging.getLogger(__name__)


class BadgeUser(models.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification User Badge'
    _order = "create_date desc"
    _rec_name = "badge_name"

    user_id = fields.Many2one('res.users', string="User", required=True, ondelete="cascade", index=True)
    sender_id = fields.Many2one('res.users', string="Sender", help="The user who has send the badge")
    badge_id = fields.Many2one('gamification.badge', string='Badge', required=True, ondelete="cascade", index=True)
    challenge_id = fields.Many2one('gamification.challenge', string='Challenge originating', help="If this badge was rewarded through a challenge")
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

    @api.model
    def create(self, vals):
        self.env['gamification.badge'].browse(vals['badge_id']).check_granting()
        return super(BadgeUser, self).create(vals)


class GamificationBadge(models.Model):
    """Badge object that users can send and receive"""

    CAN_GRANT = 1
    NOBODY_CAN_GRANT = 2
    USER_NOT_VIP = 3
    BADGE_REQUIRED = 4
    TOO_MANY = 5

    _name = 'gamification.badge'
    _description = 'Gamification Badge'
    _inherit = ['mail.thread', 'image.mixin']

    name = fields.Char('Badge', required=True, translate=True)
    active = fields.Boolean('Active', default=True)
    description = fields.Text('Description', translate=True)
    level = fields.Selection([
        ('bronze', 'Bronze'), ('silver', 'Silver'), ('gold', 'Gold')],
        string='Forum Badge Level', default='bronze')

    rule_auth = fields.Selection([
            ('everyone', 'Everyone'),
            ('users', 'A selected list of users'),
            ('having', 'People having some badges'),
            ('nobody', 'No one, assigned through challenges'),
        ], default='everyone',
        string="Allowance to Grant", help="Who can grant this badge", required=True)
    rule_auth_user_ids = fields.Many2many(
        'res.users', 'rel_badge_auth_users',
        string='Authorized Users',
        help="Only these people can give this badge")
    rule_auth_badge_ids = fields.Many2many(
        'gamification.badge', 'gamification_badge_rule_badge_rel', 'badge1_id', 'badge2_id',
        string='Required Badges',
        help="Only the people having these badges can give this badge")

    rule_max = fields.Boolean('Monthly Limited Sending', help="Check to set a monthly limit per person of sending this badge")
    rule_max_number = fields.Integer('Limitation Number', help="The maximum number of time this badge can be sent per month per person.")
    challenge_ids = fields.One2many('gamification.challenge', 'reward_id', string="Reward of Challenges")

    goal_definition_ids = fields.Many2many(
        'gamification.goal.definition', 'badge_unlocked_definition_rel',
        string='Rewarded by', help="The users that have succeeded theses goals will receive automatically the badge.")

    owner_ids = fields.One2many(
        'gamification.badge.user', 'badge_id',
        string='Owners', help='The list of instances of this badge granted to users')

    granted_count = fields.Integer("Total", compute='_get_owners_info', help="The number of time this badge has been received.")
    granted_users_count = fields.Integer("Number of users", compute='_get_owners_info', help="The number of time this badge has been received by unique users.")
    unique_owner_ids = fields.Many2many(
        'res.users', string="Unique Owners", compute='_get_owners_info',
        help="The list of unique users having received this badge.")

    stat_this_month = fields.Integer(
        "Monthly total", compute='_get_badge_user_stats',
        help="The number of time this badge has been received this month.")
    stat_my = fields.Integer(
        "My Total", compute='_get_badge_user_stats',
        help="The number of time the current user has received this badge.")
    stat_my_this_month = fields.Integer(
        "My Monthly Total", compute='_get_badge_user_stats',
        help="The number of time the current user has received this badge this month.")
    stat_my_monthly_sending = fields.Integer(
        'My Monthly Sending Total',
        compute='_get_badge_user_stats',
        help="The number of time the current user has sent this badge this month.")

    remaining_sending = fields.Integer(
        "Remaining Sending Allowed", compute='_remaining_sending_calc',
        help="If a maximum is set")

    @api.depends('owner_ids')
    def _get_owners_info(self):
        """Return:
            the list of unique res.users ids having received this badge
            the total number of time this badge was granted
            the total number of users this badge was granted to
        """
        defaults = {
            'granted_count': 0,
            'granted_users_count': 0,
            'unique_owner_ids': [],
        }
        if not self.ids:
            self.update(defaults)
            return

        self.env.cr.execute("""
            SELECT badge_id, count(user_id) as granted_count,
                count(distinct(user_id)) as granted_users_count,
                array_agg(distinct(user_id)) as unique_owner_ids
            FROM gamification_badge_user
            WHERE badge_id in %s
            GROUP BY badge_id
            """, [tuple(self.ids)])

        mapping = {
            badge_id: {
                'granted_count': count,
                'granted_users_count': distinct_count,
                'unique_owner_ids': owner_ids,
            }
            for (badge_id, count, distinct_count, owner_ids) in self.env.cr._obj
        }
        for badge in self:
            badge.update(mapping.get(badge.id, defaults))

    @api.depends('owner_ids.badge_id', 'owner_ids.create_date', 'owner_ids.user_id')
    def _get_badge_user_stats(self):
        """Return stats related to badge users"""
        first_month_day = date.today().replace(day=1)

        for badge in self:
            owners = badge.owner_ids
            badge.stat_my = sum(o.user_id == self.env.user for o in owners)
            badge.stat_this_month = sum(o.create_date.date() >= first_month_day for o in owners)
            badge.stat_my_this_month = sum(
                o.user_id == self.env.user and o.create_date.date() >= first_month_day
                for o in owners
            )
            badge.stat_my_monthly_sending = sum(
                o.create_uid == self.env.user and o.create_date.date() >= first_month_day
                for o in owners
            )

    @api.depends(
        'rule_auth',
        'rule_auth_user_ids',
        'rule_auth_badge_ids',
        'rule_max',
        'rule_max_number',
        'stat_my_monthly_sending',
    )
    def _remaining_sending_calc(self):
        """Computes the number of badges remaining the user can send

        0 if not allowed or no remaining
        integer if limited sending
        -1 if infinite (should not be displayed)
        """
        for badge in self:
            if badge._can_grant_badge() != self.CAN_GRANT:
                # if the user cannot grant this badge at all, result is 0
                badge.remaining_sending = 0
            elif not badge.rule_max:
                # if there is no limitation, -1 is returned which means 'infinite'
                badge.remaining_sending = -1
            else:
                badge.remaining_sending = badge.rule_max_number - badge.stat_my_monthly_sending

    def check_granting(self):
        """Check the user 'uid' can grant the badge 'badge_id' and raise the appropriate exception
        if not

        Do not check for SUPERUSER_ID
        """
        status_code = self._can_grant_badge()
        if status_code == self.CAN_GRANT:
            return True
        elif status_code == self.NOBODY_CAN_GRANT:
            raise exceptions.UserError(_('This badge can not be sent by users.'))
        elif status_code == self.USER_NOT_VIP:
            raise exceptions.UserError(_('You are not in the user allowed list.'))
        elif status_code == self.BADGE_REQUIRED:
            raise exceptions.UserError(_('You do not have the required badges.'))
        elif status_code == self.TOO_MANY:
            raise exceptions.UserError(_('You have already sent this badge too many time this month.'))
        else:
            _logger.error("Unknown badge status code: %s" % status_code)
        return False

    def _can_grant_badge(self):
        """Check if a user can grant a badge to another user

        :param uid: the id of the res.users trying to send the badge
        :param badge_id: the granted badge id
        :return: integer representing the permission.
        """
        if self.env.is_admin():
            return self.CAN_GRANT

        if self.rule_auth == 'nobody':
            return self.NOBODY_CAN_GRANT
        elif self.rule_auth == 'users' and self.env.user not in self.rule_auth_user_ids:
            return self.USER_NOT_VIP
        elif self.rule_auth == 'having':
            all_user_badges = self.env['gamification.badge.user'].search([('user_id', '=', self.env.uid)]).mapped('badge_id')
            if self.rule_auth_badge_ids - all_user_badges:
                return self.BADGE_REQUIRED

        if self.rule_max and self.stat_my_monthly_sending >= self.rule_max_number:
            return self.TOO_MANY

        # badge.rule_auth == 'everyone' -> no check
        return self.CAN_GRANT
