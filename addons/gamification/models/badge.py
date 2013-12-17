# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.translate import _

# from templates import TemplateHelper
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class gamification_badge_user(osv.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification user badge'
    _order = "create_date desc"

    _columns = {
        'user_id': fields.many2one('res.users', string="User", required=True),
        'badge_id': fields.many2one('gamification.badge', string='Badge', required=True),
        'comment': fields.text('Comment'),
        'badge_name': fields.related('badge_id', 'name', type="char", string="Badge Name"),
        'create_date': fields.datetime('Created', readonly=True),
        'create_uid': fields.many2one('res.users', 'Creator', readonly=True),
    }


class gamification_badge(osv.Model):
    """Badge object that users can send and receive"""

    _name = 'gamification.badge'
    _description = 'Gamification badge'
    _inherit = ['mail.thread']

    def _get_owners_info(self, cr, uid, ids, name, args, context=None):
        """Return:
            the list of unique res.users ids having received this badge
            the total number of time this badge was granted
            the total number of users this badge was granted to
        """
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            res = set()
            for owner in obj.owner_ids:
                res.add(owner.user_id.id)
            res = list(res)
            result[obj.id] = {
                'unique_owner_ids': res,
                'stat_count': len(obj.owner_ids),
                'stat_count_distinct': len(res)
            }
        return result

    def _get_badge_user_stats(self, cr, uid, ids, name, args, context=None):
        """Return stats related to badge users"""
        result = dict.fromkeys(ids, False)
        badge_user_obj = self.pool.get('gamification.badge.user')
        first_month_day = date.today().replace(day=1).strftime(DF)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {
                'stat_my': badge_user_obj.search(cr, uid, [('badge_id', '=', obj.id), ('user_id', '=', uid)], context=context, count=True),
                'stat_this_month': badge_user_obj.search(cr, uid, [('badge_id', '=', obj.id), ('create_date', '>=', first_month_day)], context=context, count=True),
                'stat_my_this_month': badge_user_obj.search(cr, uid, [('badge_id', '=', obj.id), ('user_id', '=', uid), ('create_date', '>=', first_month_day)], context=context, count=True),
                'stat_my_monthly_sending': badge_user_obj.search(cr, uid, [('badge_id', '=', obj.id), ('create_uid', '=', uid), ('create_date', '>=', first_month_day)], context=context, count=True)
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
            if self._can_grant_badge(cr, uid, uid, badge.id, context) != 1:
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
        'description': fields.text('Description'),
        'image': fields.binary("Image", help="This field holds the image used for the badge, limited to 256x256"),
        # image_select: selection with a on_change to fill image with predefined picts
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
            'rel_badge_badge', 'badge1_id', 'badge2_id',
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
    }

    def send_badge(self, cr, uid, badge_id, badge_user_ids, user_from=False, context=None):
        """Send a notification to a user for receiving a badge

        Does NOT verify constrains on badge granting.
        The users are added to the owner_ids (create badge_user if needed)
        The stats counters are incremented
        :param badge_id: id of the badge to deserve
        :param badge_user_ids: list(int) of badge users that will receive the badge
        :param user_from: optional id of the res.users object that has sent the badge
        """
        badge = self.browse(cr, uid, badge_id, context=context)
        # template_env = TemplateHelper()

        res = None
        temp_obj = self.pool.get('email.template')
        template_id = self.pool['ir.model.data'].get_object(cr, uid, 'gamification', 'email_template_badge_received', context)
        ctx = context.copy()
        for badge_user in self.pool.get('gamification.badge.user').browse(cr, uid, badge_user_ids, context=context):

            ctx.update({'user_from': self.pool.get('res.users').browse(cr, uid, user_from).name})

            body_html = temp_obj.render_template(cr, uid, template_id.body_html, 'gamification.badge.user', badge_user.id, context=ctx)

            # as SUPERUSER as normal user don't have write access on a badge
            res = self.message_post(cr, SUPERUSER_ID, badge.id, partner_ids=[badge_user.user_id.partner_id.id], body=body_html, type='comment', subtype='mt_comment', context=context)
        return res

    def check_granting(self, cr, uid, user_from_id, badge_id, context=None):
        """Check the user 'user_from_id' can grant the badge 'badge_id' and raise the appropriate exception
        if not"""
        status_code = self._can_grant_badge(cr, uid, user_from_id, badge_id, context=context)
        if status_code == 1:
            return True
        elif status_code == 2:
            raise osv.except_osv(_('Warning!'), _('This badge can not be sent by users.'))
        elif status_code == 3:
            raise osv.except_osv(_('Warning!'), _('You are not in the user allowed list.'))
        elif status_code == 4:
            raise osv.except_osv(_('Warning!'), _('You do not have the required badges.'))
        elif status_code == 5:
            raise osv.except_osv(_('Warning!'), _('You have already sent this badge too many time this month.'))
        else:
            _logger.exception("Unknown badge status code: %d" % int(status_code))
        return False

    def _can_grant_badge(self, cr, uid, user_from_id, badge_id, context=None):
        """Check if a user can grant a badge to another user

        :param user_from_id: the id of the res.users trying to send the badge
        :param badge_id: the granted badge id
        :return: integer representing the permission.
            1: can grant
            2: nobody can send
            3: user not in the allowed list
            4: don't have the required badges
            5: user's monthly limit reached
        """
        badge = self.browse(cr, uid, badge_id, context=context)

        if badge.rule_auth == 'nobody':
            return 2

        elif badge.rule_auth == 'users' and user_from_id not in [user.id for user in badge.rule_auth_user_ids]:
            return 3

        elif badge.rule_auth == 'having':
            all_user_badges = self.pool.get('gamification.badge.user').search(cr, uid, [('user_id', '=', user_from_id)], context=context)
            for required_badge in badge.rule_auth_badge_ids:
                if required_badge.id not in all_user_badges:
                    return 4

        if badge.rule_max and badge.stat_my_monthly_sending >= badge.rule_max_number:
            return 5

        # badge.rule_auth == 'everyone' -> no check
        return 1


class grant_badge_wizard(osv.TransientModel):
    """ Wizard allowing to grant a badge to a user"""

    _name = 'gamification.badge.user.wizard'
    _columns = {
        'user_id': fields.many2one("res.users", string='User', required=True),
        'badge_id': fields.many2one("gamification.badge", string='Badge', required=True),
        'comment': fields.text('Comment'),
    }

    def action_grant_badge(self, cr, uid, ids, context=None):
        """Wizard action for sending a badge to a chosen user"""

        badge_obj = self.pool.get('gamification.badge')
        badge_user_obj = self.pool.get('gamification.badge.user')

        for wiz in self.browse(cr, uid, ids, context=context):
            if uid == wiz.user_id.id:
                raise osv.except_osv(_('Warning!'), _('You can not grant a badge to yourself'))

            #check if the badge granting is legitimate
            if badge_obj.check_granting(cr, uid, user_from_id=uid, badge_id=wiz.badge_id.id, context=context):
                #create the badge
                values = {
                    'user_id': wiz.user_id.id,
                    'badge_id': wiz.badge_id.id,
                    'comment': wiz.comment,
                }
                badge_user = badge_user_obj.create(cr, uid, values, context=context)
                #notify the user
                result = badge_obj.send_badge(cr, uid, wiz.badge_id.id, [badge_user], user_from=uid, context=context)

        return result
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
