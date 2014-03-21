# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp
from openerp.osv import osv, fields
from openerp.tools.translate import _

class gamification_challenge(osv.Model):
    _inherit = 'gamification.challenge'

    def _get_categories(self, cr, uid, context=None):
        res = super(gamification_challenge, self)._get_categories(cr, uid, context=context)
        res.append(('forum', 'Website / Forum'))
        return res

    _columns = {
        'category': fields.selection(lambda s, *a, **k: s._get_categories(*a, **k),
            string="Appears in", help="Define the visibility of the challenge through menus", required=True),
    }

    def check_challenge_reward(self, cr, uid, ids, force=False, context=None):
        """NOTE: gamification module never assigns reward for and on going challenge,
         here we need to assign badges to the users who have completed their goal."""
        if isinstance(ids, (int,long)):
            ids = [ids]
        context = context or {}
        badge_user_obj = self.pool.get('gamification.badge.user');
        super(gamification_challenge, self).check_challenge_reward(cr, uid, ids, force=False, context=context)
        for challenge in self.browse(cr, uid, ids, context=context):
            if challenge.category == 'forum':
                rewarded_users = []
                for user in challenge.user_ids:
                    bages_user_ids = badge_user_obj.search(cr, uid, [('user_id', '=', user.id),('badge_id', '=', challenge.reward_id.id)],context=None)
                    # if user not rewarded before then give reward.
                    if not bages_user_ids:
                        reached_goal_ids = self.pool.get('gamification.goal').search(cr, uid, [
                            ('challenge_id', '=', challenge.id),
                            ('user_id', '=', user.id),
                            ('state', '=', 'reached'),
                        ], context=context)
                        if len(reached_goal_ids) == len(challenge.line_ids):
                            self.reward_user(cr, uid, user.id, challenge.reward_id.id, context)
                            rewarded_users.append(user)
                if rewarded_users:
                    message_body = _("Reward (badge %s) for every succeeding user was sent to %s." % (challenge.reward_id.name, ", ".join([user.name for user in rewarded_users])))
                    self.message_post(cr, uid, challenge.id, body=message_body, context=context)
        return True

class Badge(osv.Model):
    _inherit = 'gamification.badge'
    _columns = {
        'level': fields.selection([('bronze', 'bronze'), ('silver', 'silver'), ('gold', 'gold')], 'Forum Badge Level'),
    }

