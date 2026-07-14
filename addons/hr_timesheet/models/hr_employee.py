# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    has_timesheet = fields.Boolean(compute='_compute_has_timesheet', groups="hr.group_hr_user,base.group_system", export_string_translation=False)

    def _compute_has_timesheet(self):
        self.env.cr.execute("""
        SELECT id, EXISTS(SELECT 1 FROM account_analytic_line WHERE project_id IS NOT NULL AND employee_id = e.id limit 1)
          FROM hr_employee e
         WHERE id in %s
        """, (tuple(self.ids), ))

        result = {eid[0]: eid[1] for eid in self.env.cr.fetchall()}

        for employee in self:
            employee.has_timesheet = result.get(employee.id, False)

    @api.depends('company_id', 'user_id')
    @api.depends_context('allowed_company_ids')
    def _compute_display_name(self):
        super()._compute_display_name()
        allowed_company_ids = self.env.context.get('allowed_company_ids', [])
        if len(allowed_company_ids) <= 1:
            return

        employees_count_per_user = {
            user.id: count
            for user, count in self.env['hr.employee'].sudo()._read_group(
                [('user_id', 'in', self.user_id.ids), ('company_id', 'in', allowed_company_ids)],
                ['user_id'],
                ['__count'],
            )
        }
        for employee in self:
            if employees_count_per_user.get(employee.user_id.id, 0) > 1:
                employee.display_name = f'{employee.display_name} - {employee.company_id.name}'

    def action_unlink_wizard(self):
        wizard = self.env['hr.employee.delete.wizard'].create({
            'employee_ids': self.ids,
        })
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver') and wizard.has_timesheet and not wizard.has_active_employee:
            raise UserError(_('You cannot delete employees who have timesheets.'))

        return {
            'name': _('Confirmation'),
            'view_mode': 'form',
            'res_model': 'hr.employee.delete.wizard',
            'views': [(self.env.ref('hr_timesheet.hr_employee_delete_wizard_form').id, 'form')],
            'type': 'ir.actions.act_window',
            'res_id': wizard.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_timesheet_from_employee(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("hr_timesheet.timesheet_action_from_employee")
        context = literal_eval(action['context'].replace('active_id', str(self.id)))
        context['create'] = context.get('create', True) and self.active
        action['context'] = context
        return action
