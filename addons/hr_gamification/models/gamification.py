# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GamificationBadgeUser(models.Model):
    """User having received a badge"""
    _inherit = 'gamification.badge.user'

    employee_id = fields.Many2one('hr.employee', string='Employee', index=True)
    has_edit_delete_access = fields.Boolean(compute="_compute_has_edit_delete_access")

    @api.constrains('employee_id')
    def _check_employee_related_user(self):
        for badge_user in self:
            if badge_user.employee_id and badge_user.employee_id not in badge_user.user_id.\
                with_context(allowed_company_ids=badge_user.user_id.company_ids.ids).employee_ids:
                raise ValidationError(_('The selected employee does not correspond to the selected user.'))

    def _compute_has_edit_delete_access(self):
        is_hr_user = self.env.user.has_group('hr.group_hr_user')
        for badge_user in self:
            badge_user.has_edit_delete_access = is_hr_user or self.env.uid == self.create_uid.id

    def action_open_badge(self):
        self.ensure_one()
        return {
            'name': _('Received Badge'),
            'type': 'ir.actions.act_window',
            'res_model': 'gamification.badge.user',
            'res_id': self.id,
            'target': 'new',
            'view_mode': 'form',
            'view_id': self.env.ref("hr_gamification.view_current_badge_form").id,
            'context': {"dialog_size": "medium"},
        }

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(message, model_description, msg_vals)
        self.ensure_one()
        base_url = self.get_base_url()
        for group in groups:
            if group[0] == 'user':
                if self.employee_id:
                    employee_form_url = f"{base_url}/web#action=hr.hr_employee_public_action&id={self.employee_id.id}&open_badges_tab=true&user_badge_id={self.id}"

                    group[2]['button_access'] = {
                        'url': employee_form_url,
                        'title': _('View Your Badge'),
                    }
                    group[2]['has_button_access'] = True
                else:
                    group[2]['has_button_access'] = False
        return groups


class GamificationBadge(models.Model):
    _inherit = 'gamification.badge'

    granted_employees_count = fields.Integer(compute="_compute_granted_employees_count")

    @api.depends('owner_ids.employee_id')
    def _compute_granted_employees_count(self):
        user_count = dict(
            self.env['gamification.badge.user']._read_group(
                [('badge_id', 'in', self.ids), ('employee_id', '!=', False)],
                ['badge_id'], ['__count'],
            ),
        )
        for badge in self:
            badge.granted_employees_count = user_count.get(badge._origin, 0)

    def get_granted_employees(self):
        employee_ids = self.mapped('owner_ids.employee_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Granted Employees',
            'view_mode': 'kanban,list,form',
            'res_model': 'hr.employee.public',
            'domain': [('id', 'in', employee_ids)]
        }
