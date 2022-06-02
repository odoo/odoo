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
            if badge_user.employee_id not in badge_user.user_id.employee_ids:
                raise ValidationError(_('The selected employee does not correspond to the selected user.'))


class GamificationBadge(models.Model):
    _inherit = 'gamification.badge'

    granted_employees_count = fields.Integer(compute="_compute_granted_employees_count")

    @api.depends('owner_ids.employee_id')
    def _compute_granted_employees_count(self):
        badge_data = self.env['gamification.badge.user']._read_group(
            [('badge_id', 'in', self.ids), ('employee_id', '!=', False)], ['badge_id'], ['badge_id']
        )
        badge_count = {c['badge_id'][0]: c['badge_id_count'] for c in badge_data}
        for badge in self:
            badge.granted_employees_count = badge_count.get(badge.id, 0)

    def get_granted_employees(self):
        employee_ids = self.mapped('owner_ids.employee_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Granted Employees',
            'view_mode': 'kanban,tree,form',
            'res_model': 'hr.employee.public',
            'domain': [('id', 'in', employee_ids)]
        }
