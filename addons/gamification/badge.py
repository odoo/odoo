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


class gamification_badge_user(osv.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification user badge'

    _columns = {
        'employee_id': fields.many2one("hr.employee", string='Employee', required=True),
        'user_id': fields.related('employee_id', 'user_id', string="User"),
        'badge_ids': fields.many2many('gamification.badge', 'rel_badge_users', string='Badge'),  # or many2one ??
    }


class gamification_badge(osv.Model):
    """Badge object that users can send and receive"""

    _name = 'gamification.badge'
    _description = 'Gamification badge'

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    _columns = {
        'name': fields.char('Badge', required=True, translate=True),
        'description': fields.text('Description'),
        'image' : fields.binary("Image",
            help="This field holds the image used for the badge, limited to 256x256"),
        # image_select: selection with a on_change to fill image with predefined picts
        'rule_auth': fields.selection([
                ('everyone', 'Everyone'),
                ('list', 'A selected list of users'),
                ('having', 'People having some badges'),
                ('computed', 'Nobody, Computed'),
            ],
            string="Authorization Rule",
            help="Who can give this badge",
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
        'goal_type_ids': fields.many2many('gamification.goal.type',
            string='Goals Linked',
            help="The users that have succeeded theses goals will receive automatically the badge."),
        'public': fields.boolean('Public',
            help="A message will be posted on the user profile or just sent to him"),
        'owner_ids': fields.many2many('gamification.badge.user', 'rel_badge_users',
            string='Owners',
            help='The list of users having receive this badge'),
        'stat_count': fields.integer('Total Count',
            help="The number of time this badge has been received."),
        'stat_count_distinct': fields.integer('Uniaue Count',
            help="The number of time this badge has been received by individual users."),
        'stat_this_month': fields.integer('Monthly Count',
            help="The number of time this badge has been received this month."),
        # stat_my
        # stat_my_this_month
        'compute_code': fields.text('Compute Code',
            help="The python code that will be executed to verify if a user can receive this badge.")
    }

    _default = {
        'stat_count': 0,
        'stat_count_distinct': 0,
        'stat_this_month': 0,
    }

    def send_badge(self, cr, uid, badge_id, user_ids, employee_from=None, context=None):
        """Send a badge to a user

        The users are added to the owner_ids (create badge_user if needed)
        The stats counters are incremented
        :param badge_id: id of the badge to deserve
        :param user_ids: list(int) of res.users that will receive the badge
        """
        bade_user_obj = self.pool.get('gamification.badge.user')
        res_users_obj = self.pool.get('res.users')
        badge = self.browse(cr, uid, badge_id, context=context)
        template_env = TemplateHelper()

        res = None
        for user_id in user_ids:
            badge_users = bade_user_obj.search(cr, uid, [('user_id', '=', user_id)], context=context)
            if len(badge_users) == 0:
                user = res_users_obj.browse(cr, uid, user_id, context=context)
                badge_user = bade_user_obj.create(cr, uid,
                    {'user_id': user_id, 'badge_ids': [(4, badge.id)]}, context=context)
                badge_users = [badge_user.id]

            values = {
                'badge': badge,
                'badgeb64': badge.image.encode('base64'),
            }
            if employee_from:
                values['employee_from'] = employee_from
            else:
                values['employee_from'] = False
            body_html = template_env.get_template('badge_received.mako').render(values)
            res = self.pool.get('hr.employee').message_post(cr, uid, badge_users[0].employee_id,
                                                            body=body_html,
                                                            context=context)
        return res

    def check_condition(self, cr, uid, badge_id, context=None):
        """Check if the badge should be deserved to users

        Only badges with the rule_auth == 'computed' can be automatically
        granted and other type of badge will always return an empty list
        :return: list of res.users ids that should receive the badge"""

        context = context or {}

        badge = self.browse(cr, uid, badge_id, context=context)
        if badge.rule_auth != 'computed':
            return []

        code_obj = compile(badge.compute_code, '<string>', 'exec')
        code_globals = {}
        code_locals = {'cr': cr, 'uid': uid, 'context': context, 'result': []}
        exec code_obj in code_globals, code_locals
        if 'result' in code_locals and type(code_locals['result']) == list:
            user_badge_ids = self.pool.get('gamification.badge.user').search(
                cr, uid, [('user_id', 'in', code_locals['result'])], context=context)
            self.send_badge(cr, uid, badge.id, user_badge_ids, context=context)

        return True

    def grant_badge(self, cr, uid, user_from_id, user_to_id, badge_id, context=None):
        """A user wants to grant a badge to another user

        :param user_from_id: the id of the res.users trying to send the badge
        :param user_to_id: the id of the res.users that should recieve it
        :param badge_id: the granted badge id
        :return: boolean, True if succeeded to send, False otherwise"""
        context = context or {}
        badge = self.browse(cr, uid, badge_id, context=context)

        if badge.rule_auth == 'computed':
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

        user_from = self.pool.get('res.users').browse(cr, uid, user_from_id, context=context)
        if len(user_from.employee_ids) > 0:
            self.send_badge(cr, uid, badge_id, [user_to_id], employee_from=user_from.employee_ids[0], context=context)
        else:
            self.send_badge(cr, uid, badge_id, [user_to_id], context=context)

        return True
