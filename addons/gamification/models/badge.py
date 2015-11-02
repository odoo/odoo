# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.translate import _

from datetime import date
import logging
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

class gamification_badge_user(osv.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification user badge'
    _order = "create_date desc"
    _rec_name = "badge_name"

    _columns = {
        'user_id': fields.many2one('res.users', string="User", required=True, ondelete="cascade"),
        'sender_id': fields.many2one('res.users', string="Sender", help="The user who has send the badge"),
        'badge_id': fields.many2one('gamification.badge', string='Badge', required=True, ondelete="cascade"),
        'challenge_id': fields.many2one('gamification.challenge', string='Challenge originating', help="If this badge was rewarded through a challenge"),
        'comment': fields.text('Comment'),
        'badge_name': fields.related('badge_id', 'name', type="char", string="Badge Name"),
        'create_date': fields.datetime('Created', readonly=True),
        'create_uid': fields.many2one('res.users', string='Creator', readonly=True),
    }


    def _send_badge(self, cr, uid, ids, context=None):
        """Send a notification to a user for receiving a badge

        Does not verify constrains on badge granting.
        The users are added to the owner_ids (create badge_user if needed)
        The stats counters are incremented
        :param ids: list(int) of badge users that will receive the badge
        """
        res = True
        temp_obj = self.pool.get('mail.template')
        user_obj = self.pool.get('res.users')
        template_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'gamification', 'email_template_badge_received')[1]
        for badge_user in self.browse(cr, uid, ids, context=context):
            template = temp_obj.get_email_template(cr, uid, template_id, badge_user.id, context=context)
            body_html = temp_obj.render_template(cr, uid, template.body_html, 'gamification.badge.user', badge_user.id, context=template._context)
            res = user_obj.message_post(
                cr, uid, badge_user.user_id.id,
                body=body_html,
                subtype='gamification.mt_badge_granted',
                partner_ids=[badge_user.user_id.partner_id.id],
                context=context)
        return res

    def create(self, cr, uid, vals, context=None):
        self.pool.get('gamification.badge').check_granting(cr, uid, badge_id=vals.get('badge_id'), context=context)
        return super(gamification_badge_user, self).create(cr, uid, vals, context=context)


class gamification_badge(osv.Model):
    """Badge object that users can send and receive"""

    CAN_GRANT = 1
    NOBODY_CAN_GRANT = 2
    USER_NOT_VIP = 3
    BADGE_REQUIRED = 4
    TOO_MANY = 5

    _name = 'gamification.badge'
    _description = 'Gamification badge'
    _inherit = ['mail.thread']

    def _get_owners_info(self, cr, uid, ids, name, args, context=None):
        """Return:
            the list of unique res.users ids having received this badge
            the total number of time this badge was granted
            the total number of users this badge was granted to
        """
        result = dict((res_id, {'stat_count': 0, 'stat_count_distinct': 0, 'unique_owner_ids': []}) for res_id in ids)

        cr.execute("""
            SELECT badge_id, count(user_id) as stat_count,
                count(distinct(user_id)) as stat_count_distinct,
                array_agg(distinct(user_id)) as unique_owner_ids
            FROM gamification_badge_user
            WHERE badge_id in %s
            GROUP BY badge_id
            """, (tuple(ids),))
        for (badge_id, stat_count, stat_count_distinct, unique_owner_ids) in cr.fetchall():
            result[badge_id] = {
                'stat_count': stat_count,
                'stat_count_distinct': stat_count_distinct,
                'unique_owner_ids': unique_owner_ids,
            }
        return result

    def _get_badge_user_stats(self, cr, uid, ids, name, args, context=None):
        """Return stats related to badge users"""
        result = dict.fromkeys(ids, False)
        badge_user_obj = self.pool.get('gamification.badge.user')
        first_month_day = date.today().replace(day=1).strftime(DF)
        for bid in ids:
            result[bid] = {
                'stat_my': badge_user_obj.search(cr, uid, [('badge_id', '=', bid), ('user_id', '=', uid)], context=context, count=True),
                'stat_this_month': badge_user_obj.search(cr, uid, [('badge_id', '=', bid), ('create_date', '>=', first_month_day)], context=context, count=True),
                'stat_my_this_month': badge_user_obj.search(cr, uid, [('badge_id', '=', bid), ('user_id', '=', uid), ('create_date', '>=', first_month_day)], context=context, count=True),
                'stat_my_monthly_sending': badge_user_obj.search(cr, uid, [('badge_id', '=', bid), ('create_uid', '=', uid), ('create_date', '>=', first_month_day)], context=context, count=True)
            }
        return result

    def _remaining_sending_calc(self, cr, uid, ids, name, args, context=None):
        """Computes the number of badges remaining the user can send

        0 if not allowed or no remaining
        integer if limited sending
        -1 if infinite (should not be displayed)
        """
        result = dict.fromkeys(ids, False)
        for badge in self.browse(cr, uid, ids, context=context):
            if self._can_grant_badge(cr, uid, badge.id, context) != 1:
                # if the user cannot grant this badge at all, result is 0
                result[badge.id] = 0
            elif not badge.rule_max:
                # if there is no limitation, -1 is returned which means 'infinite'
                result[badge.id] = -1
            else:
                result[badge.id] = badge.rule_max_number - badge.stat_my_monthly_sending
        return result

    _columns = {
        'name': fields.char('Badge', required=True, translate=True),
        'description': fields.text('Description', translate=True),
        'image': fields.binary("Image", attachment=True,
            help="This field holds the image used for the badge, limited to 256x256"),
        'rule_auth': fields.selection([
                ('everyone', 'Everyone'),
                ('users', 'A selected list of users'),
                ('having', 'People having some badges'),
                ('nobody', 'No one, assigned through challenges'),
            ],
            string="Allowance to Grant",
            help="Who can grant this badge",
            required=True),
        'rule_auth_user_ids': fields.many2many('res.users', 'rel_badge_auth_users',
            string='Authorized Users',
            help="Only these people can give this badge"),
        'rule_auth_badge_ids': fields.many2many('gamification.badge',
            'gamification_badge_rule_badge_rel', 'badge1_id', 'badge2_id',
            string='Required Badges',
            help="Only the people having these badges can give this badge"),

        'rule_max': fields.boolean('Monthly Limited Sending',
            help="Check to set a monthly limit per person of sending this badge"),
        'rule_max_number': fields.integer('Limitation Number',
            help="The maximum number of time this badge can be sent per month per person."),
        'stat_my_monthly_sending': fields.function(_get_badge_user_stats,
            type="integer",
            string='My Monthly Sending Total',
            multi='badge_users',
            help="The number of time the current user has sent this badge this month."),
        'remaining_sending': fields.function(_remaining_sending_calc, type='integer',
            string='Remaining Sending Allowed', help="If a maxium is set"),

        'challenge_ids': fields.one2many('gamification.challenge', 'reward_id',
            string="Reward of Challenges"),

        'goal_definition_ids': fields.many2many('gamification.goal.definition', 'badge_unlocked_definition_rel',
            string='Rewarded by',
            help="The users that have succeeded theses goals will receive automatically the badge."),

        'owner_ids': fields.one2many('gamification.badge.user', 'badge_id',
            string='Owners', help='The list of instances of this badge granted to users'),
        'active': fields.boolean('Active'),
        'unique_owner_ids': fields.function(_get_owners_info,
            string='Unique Owners',
            help="The list of unique users having received this badge.",
            multi='unique_users',
            type="many2many", relation="res.users"),

        'stat_count': fields.function(_get_owners_info, string='Total',
            type="integer",
            multi='unique_users',
            help="The number of time this badge has been received."),
        'stat_count_distinct': fields.function(_get_owners_info,
            type="integer",
            string='Number of users',
            multi='unique_users',
            help="The number of time this badge has been received by unique users."),
        'stat_this_month': fields.function(_get_badge_user_stats,
            type="integer",
            string='Monthly total',
            multi='badge_users',
            help="The number of time this badge has been received this month."),
        'stat_my': fields.function(_get_badge_user_stats, string='My Total',
            type="integer",
            multi='badge_users',
            help="The number of time the current user has received this badge."),
        'stat_my_this_month': fields.function(_get_badge_user_stats,
            type="integer",
            string='My Monthly Total',
            multi='badge_users',
            help="The number of time the current user has received this badge this month."),
    }

    _defaults = {
        'rule_auth': 'everyone',
        'active': True,
    }

    def check_granting(self, cr, uid, badge_id, context=None):
        """Check the user 'uid' can grant the badge 'badge_id' and raise the appropriate exception
        if not

        Do not check for SUPERUSER_ID
        """
        status_code = self._can_grant_badge(cr, uid, badge_id, context=context)
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

    def _can_grant_badge(self, cr, uid, badge_id, context=None):
        """Check if a user can grant a badge to another user

        :param uid: the id of the res.users trying to send the badge
        :param badge_id: the granted badge id
        :return: integer representing the permission.
        """
        if uid == SUPERUSER_ID:
            return self.CAN_GRANT

        badge = self.browse(cr, uid, badge_id, context=context)

        if badge.rule_auth == 'nobody':
            return self.NOBODY_CAN_GRANT

        elif badge.rule_auth == 'users' and uid not in [user.id for user in badge.rule_auth_user_ids]:
            return self.USER_NOT_VIP

        elif badge.rule_auth == 'having':
            all_user_badges = self.pool.get('gamification.badge.user').search(cr, uid, [('user_id', '=', uid)], context=context)
            for required_badge in badge.rule_auth_badge_ids:
                if required_badge.id not in all_user_badges:
                    return self.BADGE_REQUIRED

        if badge.rule_max and badge.stat_my_monthly_sending >= badge.rule_max_number:
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
