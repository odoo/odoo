# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class hr_employee(osv.osv):
    _name = "hr.employee"
    _inherit = "hr.employee"

    def _get_employee_goals(self, cr, uid, ids, field_name, arg, context=None):
        """Return the list of goals assigned to the employee"""
        res = {}
        for employee in self.browse(cr, uid, ids, context=context):
            res[employee.id] = self.pool.get('gamification.goal').search(cr,uid,[('user_id', '=', employee.user_id.id), ('challenge_id.category', '=', 'hr')], context=context)
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
        'badge_ids': fields.function(_get_employee_badges, type="one2many", obj='gamification.badge.user', string="Employee Badges"),
        'has_badges': fields.function(_has_badges, type="boolean", string="Has Badges"),
    }
