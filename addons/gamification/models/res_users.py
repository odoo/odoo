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
from openerp.osv import osv
from challenge import MAX_VISIBILITY_RANKING

class res_users_gamification_group(osv.Model):
    """ Update of res.users class
        - if adding groups to an user, check gamification.challenge linked to
        this group, and the user. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users']

    def write(self, cr, uid, ids, vals, context=None):
        """Overwrite to autosubscribe users if added to a group marked as autojoin, user will be added to challenge"""
        write_res = super(res_users_gamification_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]

            challenge_obj = self.pool.get('gamification.challenge')
            challenge_ids = challenge_obj.search(cr, SUPERUSER_ID, [('autojoin_group_id', 'in', user_group_ids)], context=context)
            if challenge_ids:
                challenge_obj.write(cr, SUPERUSER_ID, challenge_ids, {'user_ids': [(4, user_id) for user_id in ids]}, context=context)
                challenge_obj.generate_goals_from_challenge(cr, SUPERUSER_ID, challenge_ids, context=context)
        return write_res

    def create(self, cr, uid, vals, context=None):
        """Overwrite to autosubscribe users if added to a group marked as autojoin, user will be added to challenge"""
        write_res = super(res_users_gamification_group, self).create(cr, uid, vals, context=context)
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]

            challenge_obj = self.pool.get('gamification.challenge')
            challenge_ids = challenge_obj.search(cr, SUPERUSER_ID, [('autojoin_group_id', 'in', user_group_ids)], context=context)
            if challenge_ids:
                challenge_obj.write(cr, SUPERUSER_ID, challenge_ids, {'user_ids': [(4, write_res)]}, context=context)
                challenge_obj.generate_goals_from_challenge(cr, SUPERUSER_ID, challenge_ids, context=context)
        return write_res

    # def get_goals_todo_info(self, cr, uid, context=None):

    def get_serialised_gamification_summary(self, cr, uid, context=None):
        return self._serialised_goals_summary(cr, uid, user_id=uid, context=context)

    def _serialised_goals_summary(self, cr, uid, user_id, context=None):
        """Return a serialised list of goals assigned to the user, grouped by challenge

        [
            {
                'id': <gamification.challenge id>,
                'name': <gamification.challenge name>,
                'visibility_mode': <visibility {ranking,personal}>,
                'currency': <res.currency id>,
                'lines': [(see gamification_challenge._get_serialized_challenge_lines() format)]
            },
        ]
        """
        all_goals_info = []
        challenge_obj = self.pool.get('gamification.challenge')

        user = self.browse(cr, uid, uid, context=context)
        challenge_ids = challenge_obj.search(cr, uid, [('user_ids', 'in', uid), ('state', '=', 'inprogress')], context=context)
        for challenge in challenge_obj.browse(cr, uid, challenge_ids, context=context):
            # serialize goals info to be able to use it in javascript
            lines = challenge_obj._get_serialized_challenge_lines(cr, uid, challenge, user_id, restrict_top=MAX_VISIBILITY_RANKING, context=context)
            if lines:
                all_goals_info.append({
                    'id': challenge.id,
                    'name': challenge.name,
                    'visibility_mode': challenge.visibility_mode,
                    'currency': user.company_id.currency_id.id,
                    'lines': lines,
                })

        return all_goals_info

    def get_challenge_suggestions(self, cr, uid, context=None):
        """Return the list of challenges suggested to the user"""
        challenge_info = []
        challenge_obj = self.pool.get('gamification.challenge')
        challenge_ids = challenge_obj.search(cr, uid, [('invited_user_ids', 'in', uid), ('state', '=', 'inprogress')], context=context)
        for challenge in challenge_obj.browse(cr, uid, challenge_ids, context=context):
            values = {
                'id': challenge.id,
                'name': challenge.name,
                'description': challenge.description,
            }
            challenge_info.append(values)
        return challenge_info


class res_groups_gamification_group(osv.Model):
    """ Update of res.groups class
        - if adding users from a group, check gamification.challenge linked to
        this group, and the user. This is done by overriding the write method.
    """
    _name = 'res.groups'
    _inherit = 'res.groups'

    # No need to overwrite create as very unlikely to be the value in the autojoin_group_id field
    def write(self, cr, uid, ids, vals, context=None):
        """Overwrite to autosubscribe users if add users to a group marked as autojoin, these will be added to the challenge"""
        write_res = super(res_groups_gamification_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('users'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]

            challenge_obj = self.pool.get('gamification.challenge')
            challenge_ids = challenge_obj.search(cr, SUPERUSER_ID, [('autojoin_group_id', 'in', ids)], context=context)
            if challenge_ids:
                challenge_obj.write(cr, SUPERUSER_ID, challenge_ids, {'user_ids': [(4, user_id) for user_id in user_ids]}, context=context)
                challenge_obj.generate_goals_from_challenge(cr, SUPERUSER_ID, challenge_ids, context=context)
        return write_res
