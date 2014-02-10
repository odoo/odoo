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

from openerp.osv import fields, osv
from openerp.tools.translate import _

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
                raise osv.except_osv(_('Warning!'), _('You can send badges only to employees linked to a user.'))

            if uid == wiz.user_id.id:
                raise osv.except_osv(_('Warning!'), _('You can not send a badge to yourself'))

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