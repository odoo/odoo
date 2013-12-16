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
from openerp.tools.translate import _
from openerp import SUPERUSER_ID


class hr_gamification_badge_user(osv.Model):
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


class gamification_badge(osv.Model):
    _name = 'gamification.badge'
    _inherit = ['gamification.badge']

    def message_post(self, cr, uid, thread_id, context=None, **kwargs):
        """Overwrite the message_post method to send the badge to the employee"""
        # badge_user included in the send_badge method and 'badge_id' in the wizard view
        if 'badge_user' in context and 'badge_id' in context:
            badge = self.browse(cr, uid, context['badge_id'], context=context)
            badge_user = context['badge_user']
            if badge_user.employee_id:
                return self.pool.get('hr.employee').message_post(cr, SUPERUSER_ID,
                    badge_user.employee_id.id, context=context, **kwargs)
        return super(gamification_badge, self).message_post(cr, uid, thread_id, context=context, **kwargs)

    def get_granted_employees(self, cr, uid, badge_ids, context=None):
        if context is None:
            context = {}

        employee_ids = []
        badge_user_ids = self.pool.get('gamification.badge.user').search(cr, uid, [('badge_id', 'in', badge_ids), ('employee_id', '!=', False)], context=context)
        for badge_user in self.pool.get('gamification.badge.user').browse(cr, uid, badge_user_ids, context):
            employee_ids.append(badge_user.employee_id.id)
        # remove duplicates
        employee_ids = list(set(employee_ids))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Granted Employees',
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', employee_ids)]
        }

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

        badge_obj = self.pool.get('gamification.badge')
        badge_user_obj = self.pool.get('gamification.badge.user')

        for wiz in self.browse(cr, uid, ids, context=context):
            if not wiz.user_id:
                raise osv.except_osv(_('Warning!'), _('You can send badges only to employees linked to a user.'))

            if uid == wiz.user_id.id:
                raise osv.except_osv(_('Warning!'), _('You can not send a badge to yourself'))

            if badge_obj.check_granting(cr, uid,
                                         user_from_id=uid,
                                         badge_id=wiz.badge_id.id,
                                         context=context):

                values = {
                    'user_id': wiz.user_id.id,
                    'badge_id': wiz.badge_id.id,
                    'employee_id': wiz.employee_id.id,
                    'comment': wiz.comment,
                }
                badge_user = badge_user_obj.create(cr, uid, values, context=context)

                result = badge_obj.send_badge(cr, uid, wiz.badge_id.id, [badge_user], user_from=uid, context=context)
        return result


class hr_employee(osv.osv):
    _name = "hr.employee"
    _inherit = "hr.employee"

    def _get_employee_goals(self, cr, uid, ids, field_name, arg, context=None):
        """Return the list of goals assigned to the employee"""
        res = {}
        for employee in self.browse(cr, uid, ids, context=context):
            res[employee.id] = self.pool.get('gamification.goal').search(cr,uid,[('user_id', '=', employee.user_id.id), ('plan_id.category', '=', 'hr')], context=context)
        return res

    def _get_employee_badges(self, cr, uid, ids, field_name, arg, context=None):
        """Return the list of badge_users assigned to the employee"""
        res = {}
        for employee in self.browse(cr, uid, ids, context=context):
            res[employee.id] = self.pool.get('gamification.badge.user').search(cr, uid, [
                '|',
                    ('employee_id', '=', employee.id),
                    '&',
                        ('employee_id', '=', False),
                        ('user_id', '=', employee.user_id.id)
                ], context=context)
        return res

    def _has_badges(self, cr, uid, ids, field_name, arg, context=None):
        """Return the list of badge_users assigned to the employee"""
        res = {}
        for employee in self.browse(cr, uid, ids, context=context):
            employee_badge_ids = self.pool.get('gamification.badge.user').search(cr, uid, [
                '|',
                    ('employee_id', '=', employee.id),
                    '&',
                        ('employee_id', '=', False),
                        ('user_id', '=', employee.user_id.id)
                ], context=context)
            res[employee.id] = len(employee_badge_ids) > 0
        return res

    _columns = {
        'goal_ids': fields.function(_get_employee_goals, type="one2many", obj='gamification.goal', string="Employee HR Goals"),
        'badge_ids': fields.function(_get_employee_badges, type="one2many",
            obj='gamification.badge.user', string="Employee Badges"),
        'has_badges': fields.function(_has_badges, type="boolean", string="Has Badges"),
    }
