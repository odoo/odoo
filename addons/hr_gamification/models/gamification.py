# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError


class GamificationBadgeUser(models.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _inherit = ['gamification.badge.user']

    employee_id = fields.Many2one("hr.employee", string='Employee')

    @api.one
    @api.constrains('employee_id')
    def _check_employee_id(self):
        if self.user_id and self.employee_id and self.employee_id not in self.user_id.employee_ids:
            raise ValidationError(_('The selected employee does not correspond to the selected user.'))


class GamificationBadge(models.Model):
    _name = 'gamification.badge'
    _inherit = ['gamification.badge']

    @api.multi
    def get_granted_employees(self):
        employee_ids = self.env['gamification.badge.user'].search([
            ('badge_id', 'in', self.ids),
            ('employee_id', '!=', False)
        ]).mapped('employee_id.id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Granted Employees',
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', employee_ids)]
        }
