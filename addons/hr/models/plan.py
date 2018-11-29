# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class PlanActivityType(models.Model):
    _name = 'hr.plan.activity.type'
    _description = 'Plan activity type'

    activity_type_id = fields.Many2one('mail.activity.type', 'Activity Type',
                                       domain=lambda self: [('res_model_id', '=', self.env['ir.model']._get('hr.employee').id)])
    name = fields.Char(related='activity_type_id.name')
    responsible = fields.Selection([
        ('coach', 'Coach'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
        ('other', 'Other')], default='employee', string='Responsible')
    responsible_id = fields.Many2one('res.users', 'Responsible Person')

    def get_responsible_id(self, employee_id):
        if self.responsible == 'coach':
            self.responsible_id = employee_id.coach_id.user_id
            if not self.responsible_id:
                raise UserError(_('No user linked to the coach of %s. Please contact an administrator.') % employee_id.name)
        elif self.responsible == 'manager':
            self.responsible_id = employee_id.parent_id.user_id
            if not self.responsible_id:
                raise UserError(_('No user linked to the manager of %s. Please contact an administrator.') % employee_id.name)
        elif self.responsible == 'employee':
            self.responsible_id = employee_id.user_id
            if not self.responsible_id:
                raise UserError(_('No user linked to the employee %s. Please contact an administrator.') % employee_id.name)
        return self.responsible_id


class Plan(models.Model):
    _name = 'hr.plan'
    _description = 'plan'

    name = fields.Char('Name', required=True)
    plan_activity_type_ids = fields.Many2many('hr.plan.activity.type', string='Activities')
    active = fields.Boolean(default=True)
