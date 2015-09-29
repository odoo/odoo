# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


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

        badge_user_obj = self.pool.get('gamification.badge.user')

        for wiz in self.browse(cr, uid, ids, context=context):
            if uid == wiz.user_id.id:
                raise UserError(_('You can not grant a badge to yourself'))

            #create the badge
            values = {
                'user_id': wiz.user_id.id,
                'sender_id': uid,
                'badge_id': wiz.badge_id.id,
                'comment': wiz.comment,
            }
            badge_user = badge_user_obj.create(cr, uid, values, context=context)
            result = badge_user_obj._send_badge(cr, uid, badge_user, context=context)

        return result
