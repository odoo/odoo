# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class hr_grant_badge_wizard(osv.TransientModel):
    _name = 'gamification.badge.user.wizard'
    _inherit = ['gamification.badge.user.wizard']

    _columns = {
        'employee_id': fields.many2one("hr.employee", string='Employee', required=True),
        'user_id': fields.related("employee_id", "user_id",
                                  type="many2one", relation="res.users",
                                  store=True, string='User')
    }

    def action_grant_badge(self, cr, uid, ids, context=None):
        """Wizard action for sending a badge to a chosen employee"""
        if context is None:
            context = {}

        badge_user_obj = self.pool.get('gamification.badge.user')

        for wiz in self.browse(cr, uid, ids, context=context):
            if not wiz.user_id:
                raise UserError(_('You can send badges only to employees linked to a user.'))

            if uid == wiz.user_id.id:
                raise UserError(_('You can not send a badge to yourself'))

            values = {
                'user_id': wiz.user_id.id,
                'sender_id': uid,
                'badge_id': wiz.badge_id.id,
                'employee_id': wiz.employee_id.id,
                'comment': wiz.comment,
            }

            badge_user = badge_user_obj.create(cr, uid, values, context=context)
            result = badge_user_obj._send_badge(cr, uid, [badge_user], context=context)
        return result
