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

from templates import TemplateHelper
from datetime import date


class gamification_badge_user(osv.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification user badge'

    _columns = {
        'user_id': fields.many2one('res.users', string="User", required=True),
        'badge_id': fields.many2one('gamification.badge', string='Badge'),
    }


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
                cr, uid, [('badge_id', '=', obj.id), ('user_id', '=', uid)
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
                ('nobody', 'Nobody'),
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
        'rule_max': fields.boolean('Limited',
            help="This badge can not be send indefinitely"),
        'rule_max_number': fields.integer('Limitation Number',
            help="The maximum number of time this badge can be sent per month."),

        'rule_automatic': fields.selection([
                ('manual', 'Given by Users Only'),
                ('goals', 'List of Goals'),
                ('python', 'Python Code'),
            ],
            string="Automatic Rule",
            help="Can this badge be automatically rewarded",
            required=True),

        'compute_code': fields.text('Compute Code',
            help="The python code that will be executed to verify if a user can receive this badge."),
        'goal_type_ids': fields.many2many('gamification.goal.type',
            string='Goals Linked',
            help="The users that have succeeded theses goals will receive automatically the badge."),

        'public': fields.boolean('Public',
            help="A message will be posted on the user profile or just sent to him"),
        'owner_ids': fields.one2many('gamification.badge.user', 'badge_id',
            string='Owners', help='The list of instances of this badge granted to users'),

        'stat_count': fields.function(_get_global_count, string='Total',
            help="The number of time this badge has been received."),
        'stat_count_distinct': fields.function(_get_unique_global_count,
            string='Unique Count',
            help="The number of time this badge has been received by individual users."),
        'stat_this_month': fields.function(_get_month_count,
            string='Monthly Count',
            help="The number of time this badge has been received this month."),
        'stat_my': fields.function(_get_global_my_count, string='My Total',
            help="The number of time the current user has received this badge."),
        'stat_my_this_month': fields.function(_get_month_my_count,
            string='My Monthly Total',
            help="The number of time the current user has received this badge this month."),
    }

    _defaults = {
        'stat_count': 0,
        'stat_count_distinct': 0,
        'stat_this_month': 0,
        'rule_auth': 'everyone',
        'rule_automatic': 'manual',
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
            values = {
                'badge': badge,
                'badgeb64': badge.image.encode('base64'),
            }

            if user_from:
                values['user_from'] = user_from
            else:
                values['user_from'] = False
            body_html = template_env.get_template('badge_received.mako').render(values)

            res = self.message_post(cr, uid, 0,
                                    body=body_html,
                                    partner_ids=[(4, badge_user.user_id.partner_id.id)],
                                    type='comment',
                                    subtype='mt_comment',
                                    context=context)
            print(res)
        return res

    def check_condition(self, cr, uid, badge_id, context=None):
        """Check if the badge should be deserved to users

        Only badges with the rule_auth == 'computed' can be automatically
        granted and other type of badge will always return an empty list
        :return: list of res.users ids that should receive the badge"""

        context = context or {}
        badge = self.browse(cr, uid, badge_id, context=context)

        if badge.rule_automatic == 'python':
            code_obj = compile(badge.compute_code, '<string>', 'exec')
            code_globals = {}
            code_locals = {'cr': cr, 'uid': uid, 'context': context, 'result': []}
            exec code_obj in code_globals, code_locals
            if 'result' in code_locals and type(code_locals['result']) == list:
                return self.pool.get('gamification.badge.user').search(
                    cr, uid, [('user_id', 'in', code_locals['result'])], context=context)
                # self.send_badge(cr, uid, badge.id, user_badge_ids, context=context)

        elif badge.rule_automatic == 'goals':
            common_users = None
            for goal_type in badge.goal_type_ids:
                res = self.pool.get('gamification.goal').read_group(cr, uid, [
                    ('type_id', '=', goal_type.id),
                    ('state', '=', 'reached'),
                ], ['user_id', 'state', 'type_id'], ['user_id'], context=context)
                users = [goal.user_id.id for goal in res]
                if common_users is None:
                    # first type, include all
                    common_users = users
                else:
                    merged_list = [user_id for user_id in users if user_id in common_users]
                    common_users = merged_list
            return common_users

        # else  badge.rule_automatic == 'manual':

        return []

    def can_grant_badge(self, cr, uid, user_from_id, badge_id, context=None):
        """Check if a user can grant a badge to another user

        :param user_from_id: the id of the res.users trying to send the badge
        :param badge_id: the granted badge id
        :return: boolean, True if succeeded to send, False otherwise"""
        context = context or {}
        badge = self.browse(cr, uid, badge_id, context=context)

        if badge.rule_auth == 'nobody':
            return False

        elif badge.rule_auth == 'list':
            if user_from_id not in [user.id for user in badge.rule_auth_user_ids]:
                return False

        elif badge.rule_auth == 'having':
            badge_users = self.pool.get('gamification.badge.user').search(
                cr, uid, [('user_id', '=', user_from_id)], context=context)

            if len(badge_users) == 0:
                # the user_from has no badges
                return False

            owners = [owner.id for owner in badge.owner_ids]
            granted = False
            for badge_user in badge_users:
                if badge_user.id in owners:
                    granted = True
            if not granted:
                return False

        # else badge.rule_auth == 'everyone' -> no check

        if badge.rule_max and badge.stat_this_month >= badge.rule_max_number:
            # sent the maximum number of time this month
            return False

        return True


class grant_badge_wizard(osv.TransientModel):
    _name = 'gamification.badge.user.wizard'
    _columns = {
        'user_id': fields.many2one("res.users", string='User', required=True),
        'badge_id': fields.many2one("gamification.badge", string='Badge'),
    }

    def action_grant_badge(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        badge_obj = self.pool.get('gamification.badge')
        badge_user_obj = self.pool.get('gamification.badge.user')

        for wiz in self.browse(cr, uid, ids, context=context):
            if badge_obj.can_grant_badge(cr, uid,
                                         user_from_id=uid,
                                         badge_id=wiz.badge_id.id,
                                         context=context):

                badge_user = badge_user_obj.create(cr, uid,
                        {'user_id': wiz.user_id.id, 'badge_id': wiz.badge_id.id}, context=context)
                #badge_obj.write(cr, uid, [badge.id], {'owner_ids': [(1, badge_user.id)]}, context=context)

                user_from = self.pool.get('res.users').browse(cr, uid, uid, context=context)

                badge_obj.send_badge(cr, uid, wiz.badge_id.id, [badge_user], user_from=user_from, context=context)

        return {}
grant_badge_wizard()
