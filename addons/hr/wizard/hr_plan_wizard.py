# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrPlanWizard(models.TransientModel):
    _name = 'hr.plan.wizard'
    _description = 'Plan Wizard'

    def _default_plan_id(self):
        # We know that all employees belong to the same company
        employee = self.env['hr.employee'].browse(self.env.context.get('active_ids')[0] if self.env.context.get('active_ids') else [])
        return self.env['hr.plan'].search([
            ('company_id', '=', employee.company_id.id),
            '|',
            ('department_id', '=', employee.department_id.id),
            ('department_id', '=', False)
            ], limit=1)

    plan_id = fields.Many2one('hr.plan', default=lambda self: self._default_plan_id(),
        domain="[('company_id', '=', company_id), '|', ('department_id', '=', department_id), ('department_id', '=', False)]")
    department_id = fields.Many2one(related='employee_ids.department_id')
    employee_ids = fields.Many2many(
        'hr.employee', 'hr_employee_hr_plan_wizard_rel', 'employee_id', 'plan_wizard_id', string='Employee', required=True,
        default=lambda self: self.env.context.get('active_ids', []),
    )
    company_id = fields.Many2one('res.company', 'Company', compute='_compute_company_id', required=True)
    warning = fields.Html(compute='_compute_warning')

    @api.constrains('employee_ids')
    def _check_employee_companies(self):
        for wizard in self:
            if len(wizard.employee_ids.mapped('company_id')) > 1:
                raise ValidationError(_('The employees should belong to the same company.'))

    @api.depends('employee_ids')
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.employee_ids[0].company_id

    def _get_warnings(self):
        self.ensure_one()
        warnings = set()
        for employee in self.employee_ids:
            for activity_type in self.plan_id.plan_activity_type_ids:
                warning = activity_type.get_responsible_id(employee)['warning']
                if warning:
                    warnings.add(warning)
        return warnings

    @api.depends('employee_ids', 'plan_id')
    def _compute_warning(self):
        for wizard in self:
            warnings = wizard._get_warnings()

            if warnings:
                warning_display = _('The plan %s cannot be launched: <br><ul>', wizard.plan_id.name)
                for warning in warnings:
                    warning_display += '<li>%s</li>' % warning
                warning_display += '</ul>'
            else:
                warning_display = False
            wizard.warning = warning_display

    def _get_activities_to_schedule(self):
        return self.plan_id.plan_activity_type_ids

    def action_launch(self):
        self.ensure_one()
        for employee in self.employee_ids:
            body = _('The plan %s has been started', self.plan_id.name)
            activities = set()
            for activity_type in self._get_activities_to_schedule():
                responsible = activity_type.get_responsible_id(employee)['responsible']
                if self.env['hr.employee'].with_user(responsible).check_access_rights('read', raise_exception=False):
                    date_deadline = self.env['mail.activity']._calculate_date_deadline(activity_type.activity_type_id)
                    employee.activity_schedule(
                        activity_type_id=activity_type.activity_type_id.id,
                        summary=activity_type.summary,
                        note=activity_type.note,
                        user_id=responsible.id,
                        date_deadline=date_deadline
                    )
                    activity = _('%(activity)s, assigned to %(name)s, due on the %(deadline)s', activity=activity_type.summary, name=responsible.name, deadline=date_deadline)
                    activities.add(activity)

            if activities:
                body += '<ul>'
                for activity in activities:
                    body += '<li>%s</li>' % activity
                body += '</ul>'
            employee.message_post(body=body)

        if len(self.employee_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee',
                'res_id': self.employee_ids.id,
                'name': self.employee_ids.display_name,
                'view_mode': 'form',
                'views': [(False, "form")],
            }

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'name': _('Launch Plans'),
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', self.employee_ids.ids)],
        }
