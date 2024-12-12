# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GamificationBadgeUser(models.Model):
    """User having received a badge"""
    _inherit = 'gamification.badge.user'

    employee_id = fields.Many2one('hr.employee', string='Employee', index=True)

    @api.constrains('employee_id')
    def _check_employee_related_user(self):
        for badge_user in self:
            if badge_user.employee_id and badge_user.employee_id not in badge_user.user_id.\
                with_context(allowed_company_ids=badge_user.user_id.company_ids.ids).employee_ids:
                raise ValidationError(_('The selected employee does not correspond to the selected user.'))

    def action_open_badge(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gamification.badge',
            'view_mode': 'form',
            'res_id': self.badge_id.id,
        }


class GamificationBadge(models.Model):
    _inherit = 'gamification.badge'

    granted_employees_count = fields.Integer(compute="_compute_granted_employees_count")

    @api.depends('owner_ids.employee_id')
    def _compute_granted_employees_count(self):
        for badge in self:
            badge.granted_employees_count = self.env['gamification.badge.user'].search_count([
                ('badge_id', '=', badge.id),
                ('employee_id', '!=', False)
            ])

    def get_granted_employees(self):
        employee_ids = self.mapped('owner_ids.employee_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Granted Employees',
            'view_mode': 'kanban,list,form',
            'res_model': 'hr.employee.public',
            'domain': [('id', 'in', employee_ids)]
        }
