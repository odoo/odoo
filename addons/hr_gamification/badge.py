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


class gamification_badge_user(osv.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _inherit = ['gamification.badge.user']

    _columns = {
        'employee_id': fields.many2one("hr.employee", string='Employee'),
    }

    def _check_employee_related_user(self, cr, uid, ids, context=None):
        for badge_user in self.browse(cr, uid, ids, context=context):
            if badge_user.user_id and badge_user.employee_id:
                if badge_user.employee_id not in badge_user.user_id.employee_ids:
                    return False
        return True

    _constraints = [
        (_check_employee_related_user, "The selected employee does not correspond to the selected user.", ['employee_id']),
    ]


class grant_badge_wizard(osv.TransientModel):
    _name = 'gamification.badge.user.wizard'
    _inherit = ['gamification.badge.user.wizard']

    _columns = {
        'employee_id': fields.many2one("hr.employee", string='Employee', required=True),
        'user_id': fields.related("employee_id", "user_id",
                                  type="many2one", relation="res.users",
                                  store=True, string='User'),
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

                values = {
                    'user_id': wiz.user_id.id,
                    'badge_id': wiz.badge_id.id,
                    'employee_id': wiz.employee_id.id,
                }
                badge_user = badge_user_obj.create(cr, uid, values, context=context)
                #badge_obj.write(cr, uid, [badge.id], {'owner_ids': [(1, badge_user.id)]}, context=context)

                user_from = self.pool.get('res.users').browse(cr, uid, uid, context=context)

                badge_obj.send_badge(cr, uid, wiz.badge_id.id, [badge_user], user_from=user_from, context=context)

        return {}
grant_badge_wizard()