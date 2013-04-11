# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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

from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval

from templates import TemplateHelper
from datetime import date


class gamification_badge_user(osv.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification user badge'

    _columns = {
        'user_id': fields.many2one('res.users', string="User", required=True),
        'badge_id': fields.many2one('gamification.badge', string='Badge', required=True),
        'comment': fields.text('Comment'),

        'badge_name': fields.related('badge_id', 'name', type="char", string="Badge Name"),
        'create_date': fields.datetime('Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
    }

    _order = "create_date desc"


class gamification_badge(osv.Model):
    """Badge object that users can send and receive"""

    _name = 'gamification.badge'
    _description = 'Gamification badge'
    _inherit = ['mail.thread']

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _get_global_count(self, cr, uid, ids, name, args, context=None):
        """Return the number of time this badge has been granted"""
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = len(self.pool.get('gamification.badge.user').search(
                cr, uid, [('badge_id', '=', obj.id)], context=context))
            result[obj.id] = len(obj.owner_ids)
        return result

    def _get_unique_global_list(self, cr, uid, ids, name, args, context=None):
        """Return the list of unique res.users ids having received this badge"""
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            res = self.pool.get('gamification.badge.user').read_group(
                                   cr, uid, domain=[('badge_id', '=', obj.id)],
                                   fields=['badge_id', 'user_id'],
                                   groupby=['user_id'], context=context)
            result[obj.id] = [badge_user['user_id'][0] for badge_user in res]
        return result

    def _get_unique_global_count(self, cr, uid, ids, name, args, context=None):
        """Return the number of time this badge has been granted to individual users"""
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            res = self.pool.get('gamification.badge.user').read_group(
                                   cr, uid, domain=[('badge_id', '=', obj.id)],
                                   fields=['badge_id', 'user_id'],
                                   groupby=['user_id'], context=context)
            result[obj.id] = len(res)
        return result

    def _get_month_count(self, cr, uid, ids, name, args, context=None):
        """Return the number of time this badge has been granted this month"""
        result = dict.fromkeys(ids, False)
        first_month_day = date.today().replace(day=1).isoformat()
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = len(self.pool.get('gamification.badge.user').search(
                cr, uid, [('badge_id', '=', obj.id),
                          ('create_date', '>=', first_month_day)], context=context))
        return result

    def _get_global_my_count(self, cr, uid, ids, name, args, context=None):
        """Return the number of time this badge has been granted to the current user"""
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = len(self.pool.get('gamification.badge.user').search(
                    cr, uid, [('badge_id', '=', obj.id), ('user_id', '=', uid)],
                    context=context))
        return result

    def _get_month_my_count(self, cr, uid, ids, name, args, context=None):
        """Return the number of time this badge has been granted to the current user this month"""
        result = dict.fromkeys(ids, False)
        first_month_day = date.today().replace(day=1).isoformat()
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = len(self.pool.get('gamification.badge.user').search(
                cr, uid, [('badge_id', '=', obj.id), ('user_id', '=', uid),
                          ('create_date', '>=', first_month_day)], context=context))
        return result

    def _get_month_my_sent(self, cr, uid, ids, name, args, context=None):
        """Return the number of time this badge has been granted to the current user this month"""
        result = dict.fromkeys(ids, False)
        first_month_day = date.today().replace(day=1).isoformat()
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = len(self.pool.get('gamification.badge.user').search(
                cr, uid, [('badge_id', '=', obj.id), ('create_uid', '=', uid),
                          ('create_date', '>=', first_month_day)], context=context))
        return result

    _columns = {
        'name': fields.char('Badge', required=True, translate=True),
        'description': fields.text('Description'),
        'image': fields.binary("Image",
            help="This field holds the image used for the badge, limited to 256x256"),
        # image_select: selection with a on_change to fill image with predefined picts
        'rule_auth': fields.selection([
                ('everyone', 'Everyone'),
                ('users', 'A selected list of users'),
                ('having', 'People having some badges'),
                ('nobody', 'No one'),
            ],
            string="User Authorization Rule",
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
        'stat_my_monthly_sending': fields.function(_get_month_my_sent,
            type="integer",
            string='My Monthly Sending Total',
            help="The number of time the current user has sent this badge this month."),

        'rule_automatic': fields.selection([
                ('goals', 'List of goals to reach'),
                ('python', 'Custom python code executed'),
                ('manual', 'Not automatic'),
            ],
            string="Automatic Rule",
            help="Can this badge be automatically rewarded",
            required=True),

        'compute_code': fields.char('Compute Code',
            help="The name of the python method that will be executed to verify if a user can receive this badge."),
        'goal_type_ids': fields.many2many('gamification.goal.type',
            string='Goals Linked',
            help="The users that have succeeded theses goals will receive automatically the badge."),

        'owner_ids': fields.one2many('gamification.badge.user', 'badge_id',
            string='Owners', help='The list of instances of this badge granted to users'),
        'unique_owner_ids': fields.function(_get_unique_global_list,
            string='Unique Owners',
            help="The list of unique users having received this badge.",
            type="many2many", relation="res.users"),

        'stat_count': fields.function(_get_global_count, string='Total',
            type="integer",
            help="The number of time this badge has been received."),
        'stat_count_distinct': fields.function(_get_unique_global_count,
            type="integer",
            string='Number of users',
            help="The number of time this badge has been received by individual users."),
        'stat_this_month': fields.function(_get_month_count,
            type="integer",
            string='Monthly total',
            help="The number of time this badge has been received this month."),
        'stat_my': fields.function(_get_global_my_count, string='My Total',
            type="integer",
            help="The number of time the current user has received this badge."),
        'stat_my_this_month': fields.function(_get_month_my_count,
            type="integer",
            string='My Monthly Total',
            help="The number of time the current user has received this badge this month."),
    }

    _defaults = {
        'stat_count': 0,
        'stat_count_distinct': 0,
        'stat_this_month': 0,
        'rule_auth': 'everyone',
        'rule_automatic': 'manual',
        'compute_code': "self.nobody(cr, uid, context)"
    }

    def send_badge(self, cr, uid, badge_id, badge_user_ids, user_from=None, context=None):
        """Send a notification to a user for receiving a badge

        Does NOT verify constrains on badge granting.
        The users are added to the owner_ids (create badge_user if needed)
        The stats counters are incremented
        :param badge_id: id of the badge to deserve
        :param badge_user_ids: list(int) of badge users that will receive the badge
        :param user_from: res.users object that has sent the badge
        """
        badge = self.browse(cr, uid, badge_id, context=context)
        template_env = TemplateHelper()

        res = None
        for badge_user in self.pool.get('gamification.badge.user').browse(cr, uid, badge_user_ids, context=context):
            values = {'badge_user': badge_user}

            if user_from:
                values['user_from'] = user_from
            else:
                values['user_from'] = False
            body_html = template_env.get_template('badge_received.mako').render(values)
            context['badge_user'] = badge_user

            res = self.message_post(cr, uid, badge.id,
                                    body=body_html,
                                    type='comment',
                                    subtype='mt_comment',
                                    context=context)

        return res

    def _cron_check(self, cr, uid, context=None):
        """Run cron on all automatic goals"""
        ids = self.search(cr, uid, [('rule_automatic', '!=', 'manual')], context=context)
        self.check_automatic(cr, uid, ids, context=context)

    def check_automatic(self, cr, uid, ids, context=None):
        """Check if the badges should be deserved to users

        Only badges with an automatic rule specified are checked to be
        granted, other type of badge will be skipped. Send alert messages to
        the one validating the condition.
        :param ids: the list of id of the badges to check

        In case of python code to execute, the user should input the name of
        the function that will be excuted through safe_eval. The globals
        variables available are cr (database cursor), uid (current user id)
        and context.

        To create new functions in different modules, create a class extending
        the 'gamification.badge.execute' class and implementing this method. The result
        of the function should be a list of res.users ids (int). A badge_user
        linked to this badge will be created for each of these users and a
        notification will be send.
        Beware that the case of user already having this badge is NOT checked
        and is the responsability of the python code.

        In case of list of goals to check, the case of a user already having
        this badge is checked and the user will not receive badge at each run
        of this method.
        """

        context = context or {}
        badge_user_obj = self.pool.get('gamification.badge.user')

        for badge in self.browse(cr, uid, ids, context=context):

            if badge.rule_automatic == 'python':
                values = {'cr': cr, 'uid': uid, 'context': context, 'self': self.pool.get('gamification.badge.execute')}
                result = safe_eval(badge.compute_code, values, {})

                # code_obj = compile(badge.compute_code, '<string>', 'exec')
                # code_globals = {}
                # code_locals = {'cr': cr, 'uid': uid, 'context': context, 'result': []}
                # exec code_obj in code_globals, code_locals
                if type(result) == list:
                    user_badge_ids = [
                        badge_user_obj.create(cr, uid, {'user_id': user_id, 'badge_id': badge.id}, context=context)
                        for user_id in result
                    ]
                    self.send_badge(cr, uid, badge.id, user_badge_ids, context=context)
                else:
                    raise osv.except_osv(_('Error!'), _('Unvalid return content from the evaluation of %s' % str(badge.compute_code)))

            elif badge.rule_automatic == 'goals':
                common_users = None
                for goal_type in badge.goal_type_ids:
                    res = self.pool.get('gamification.goal').read_group(cr, uid, [
                        ('type_id', '=', goal_type.id),
                        ('state', '=', 'reached'),
                    ], ['user_id', 'state', 'type_id'], ['user_id'], context=context)

                    users = [goal['user_id'][0] for goal in res]
                    if common_users is None:
                        # first type, include all
                        common_users = users
                    else:
                        merged_list = [user_id for user_id in users if user_id in common_users]
                        common_users = merged_list

                if common_users is None:
                    # nobody succeeded the goals
                    continue

                # remove users having already this badge
                badge_user_not_having = []
                for user_id in common_users:
                    badge_user_having = badge_user_obj.search(cr, uid, [
                        ('user_id', '=', user_id),
                        ('badge_id', '=', badge.id)], context=context)
                    if len(badge_user_having) == 0:
                        badge_user_not_having.append(user_id)

                # create badge users for users deserving the badge
                user_badge_ids = [
                    badge_user_obj.create(cr, uid, {'user_id': user_id, 'badge_id': badge.id}, context=context)
                    for user_id in badge_user_not_having
                ]
                self.send_badge(cr, uid, badge.id, user_badge_ids, context=context)

            # else  badge.rule_automatic == 'manual':

        return True

    def can_grant_badge(self, cr, uid, user_from_id, badge_id, context=None):
        """Check if a user can grant a badge to another user

        :param user_from_id: the id of the res.users trying to send the badge
        :param badge_id: the granted badge id
        :return: boolean, True if succeeded to send, False otherwise
        """
        context = context or {}
        badge = self.browse(cr, uid, badge_id, context=context)

        if badge.rule_auth == 'nobody':
            raise osv.except_osv(_('Warning!'), _('This badge can not be sent by users.'))

        elif badge.rule_auth == 'list':
            if user_from_id not in [user.id for user in badge.rule_auth_user_ids]:
                raise osv.except_osv(_('Warning!'), _('You are not in the user allowed list.'))

        elif badge.rule_auth == 'having':
            badge_users = self.pool.get('gamification.badge.user').search(
                cr, uid, [('user_id', '=', user_from_id)], context=context)

            if len(badge_users) == 0:
                # the user_from has no badges
                raise osv.except_osv(_('Warning!'), _('You do not have the required badges.'))

            owners = [owner.id for owner in badge.owner_ids]
            granted = False
            for badge_user in badge_users:
                if badge_user.id in owners:
                    granted = True
            if not granted:
                raise osv.except_osv(_('Warning!'), _('You do not have the required badges.'))

        # else badge.rule_auth == 'everyone' -> no check

        if badge.rule_max and badge.stat_my_monthly_sending >= badge.rule_max_number:
            # sent the maximum number of time this month
            raise osv.except_osv(_('Warning!'), _('You have already sent this badge too many time this month.'))

        return True


class grant_badge_wizard(osv.TransientModel):
    _name = 'gamification.badge.user.wizard'
    _columns = {
        'user_id': fields.many2one("res.users", string='User', required=True),
        'badge_id': fields.many2one("gamification.badge", string='Badge',  required=True),
        'comment': fields.text('Comment'),
    }

    def action_grant_badge(self, cr, uid, ids, context=None):
        """Wizard action for sending a badge to a chosen user"""
        if context is None:
            context = {}

        badge_obj = self.pool.get('gamification.badge')
        badge_user_obj = self.pool.get('gamification.badge.user')

        for wiz in self.browse(cr, uid, ids, context=context):
            if uid == wiz.user_id.id:
                raise osv.except_osv(_('Warning!'), _('You can not send a badge to yourself'))

            if badge_obj.can_grant_badge(cr, uid,
                                         user_from_id=uid,
                                         badge_id=wiz.badge_id.id,
                                         context=context):
                values = {
                    'user_id': wiz.user_id.id,
                    'badge_id': wiz.badge_id.id,
                    'comment': wiz.comment,
                }
                badge_user = badge_user_obj.create(cr, uid, values, context=context)

                user_from = self.pool.get('res.users').browse(cr, uid, uid, context=context)

                badge_obj.send_badge(cr, uid, wiz.badge_id.id, [badge_user], user_from=user_from, context=context)

        return {}
