# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


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
