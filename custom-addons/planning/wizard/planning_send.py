# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, Command, _
from odoo.osv import expression


class PlanningSend(models.TransientModel):
    _name = 'planning.send'
    _description = "Send Planning"

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        if 'slot_ids' in res and 'employee_ids' in default_fields:
            employees = self.env['planning.slot'].browse(res['slot_ids'][0][2]).employee_id
            res['employee_ids'] = [Command.set(employees.sudo().sorted('name').ids)]
        return res

    start_datetime = fields.Datetime("Period", required=True)
    end_datetime = fields.Datetime("Stop Date", required=True)
    include_unassigned = fields.Boolean("Include Open Shifts", default=True)
    note = fields.Text("Extra Message", help="Additional message displayed in the email sent to employees")
    employee_ids = fields.Many2many('hr.employee', string="Resources",
                                    help="Employees who will receive planning by email if you click on publish & send.",
                                    compute='_compute_slots_data', inverse='_inverse_employee_ids', store=True)
    slot_ids = fields.Many2many('planning.slot', compute='_compute_slots_data', store=True)
    employees_no_email = fields.Many2many('hr.employee', string="Employees without email",
                                    compute="_compute_employees_no_email", inverse="_inverse_employees_no_email")

    def _get_slot_domain(self):
        self.ensure_one()
        return [('start_datetime', '>=', self.start_datetime), ('end_datetime', '<=', self.end_datetime)]

    @api.depends('start_datetime', 'end_datetime')
    def _compute_slots_data(self):
        for wiz in self:
            wiz.slot_ids = self.env['planning.slot'].with_user(self.env.user).search(self._get_slot_domain(), order='employee_id')
            wiz.employee_ids = wiz.slot_ids.filtered(lambda s: s.resource_type == 'user').mapped('employee_id')

    def _inverse_employee_ids(self):
        for wiz in self:
            wiz.slot_ids = self.env['planning.slot'].with_user(self.env.user).search(self._get_slot_domain())

    @api.depends('employee_ids')
    def _compute_employees_no_email(self):
        for planning in self:
            planning.employees_no_email = planning.employee_ids.filtered(lambda employee: not employee.work_email)

    def _inverse_employees_no_email(self):
        for planning in self:
            planning.employee_ids = planning.employees_no_email + planning.employee_ids.filtered('work_email')

    def get_employees_without_work_email(self):
        self.ensure_one()
        if not self.employee_ids.check_access_rights('write', raise_exception=False):
            return None
        employee_ids_without_work_email = self.employee_ids.filtered(lambda employee: not employee.work_email).ids
        if not employee_ids_without_work_email:
            return None
        context = dict(self._context, force_email=True, form_view_ref='planning.hr_employee_view_form_simplified')
        return {
            'relation': 'hr.employee',
            'res_ids': employee_ids_without_work_email,
            'context': context,
        }

    def action_check_emails(self):
        if self.employees_no_email:
            return {
                'name': _('No Email Address For Some Employees'),
                'view_mode': 'form',
                'res_model': 'planning.send',
                'views': [(self.env.ref('planning.employee_no_email_list_wizard').id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': self.id,
                'target': 'new',
            }
        else:
            return self.action_send()

    def action_send(self):
        if self.include_unassigned:
            slot_to_send = self.slot_ids.filtered(lambda s: not s.employee_id or s.employee_id in self.employee_ids)
        else:
            slot_to_send = self.slot_ids.filtered(lambda s: s.employee_id in self.employee_ids)
        if not slot_to_send:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("The shifts have already been published, or there are no shifts to publish."),
                }
            }
        # create the planning
        planning = self.env['planning.planning'].create({
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'include_unassigned': self.include_unassigned,
        })
        slot_employees = slot_to_send.mapped('employee_id')
        open_slots = slot_to_send.filtered(lambda s: not s.employee_id and not s.is_past)
        employees_to_send = self.env['hr.employee']
        for employee in self.employee_ids:
            if employee in slot_employees:
                employees_to_send |= employee
            else:
                for slot in open_slots:
                    if not employee.planning_role_ids or not slot.role_id or slot.role_id in employee.planning_role_ids:
                        employees_to_send |= employee
        res = planning._send_planning(slots=slot_to_send, message=self.note, employees=employees_to_send)
        if res:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("The schedule was successfully sent to your employees."),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
