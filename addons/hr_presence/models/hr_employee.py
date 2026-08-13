# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from ast import literal_eval
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.fields import Datetime

_logger = logging.getLogger(__name__)


class Employee(models.AbstractModel):
    _inherit = 'hr.employee.base'

    email_sent = fields.Boolean(default=False)
    ip_connected = fields.Boolean(default=False)
    manually_set_present = fields.Boolean(default=False)
    manually_set_presence = fields.Boolean(default=False)

    # Stored field used in the presence kanban reporting view
    # to allow group by state.
    hr_presence_state_display = fields.Selection([
        ('out_of_working_hour', 'Out of Working Hours'),
        ('present', 'Present'),
        ('absent', 'Absent'),
        ], default='out_of_working_hour')

    @api.model
    def _check_presence(self):
        company = self.env.company
        employees = self.env['hr.employee'].search([('company_id', '=', company.id)])

        employees.write({
            'email_sent': False,
            'ip_connected': False,
            'manually_set_present': False,
            'manually_set_presence': False,
        })

        all_employees = employees


        # Check on IP
        if company.hr_presence_control_ip:
            ip_list = company.hr_presence_control_ip_list
            ip_list = ip_list.split(',') if ip_list else []
            ip_employees = self.env['hr.employee']
            for employee in employees:
                employee_ips = self.env['res.users.log'].sudo().search([
                    ('create_uid', '=', employee.user_id.id),
                    ('ip', '!=', False),
                    ('create_date', '>=', Datetime.to_string(Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)))]
                ).mapped('ip')
                if any(ip in ip_list for ip in employee_ips):
                    ip_employees |= employee
            ip_employees.write({'ip_connected': True})
            employees = employees - ip_employees

        # Check on sent emails
        if company.hr_presence_control_email:
            email_employees = self.env['hr.employee']
            threshold = company.hr_presence_control_email_amount
            for employee in employees:
                sent_emails = self.env['mail.message'].search_count([
                    ('author_id', '=', employee.user_id.partner_id.id),
                    ('date', '>=', Datetime.to_string(Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))),
                    ('date', '<=', Datetime.to_string(Datetime.now()))])
                if sent_emails >= threshold:
                    email_employees |= employee
            email_employees.write({'email_sent': True})
            employees = employees - email_employees

        company.sudo().hr_presence_last_compute_date = Datetime.now()

        for employee in all_employees:
            employee.hr_presence_state_display = employee.hr_presence_state

    def get_presence_server_action_data(self):
        server_action_xmlids = [
            'action_hr_employee_presence_present',
            'action_hr_employee_presence_absent',
            'action_hr_employee_presence_log',
            'action_hr_employee_presence_sms',
            'action_hr_employee_presence_time_off',
        ]
        actions = self.env['ir.actions.server'].sudo()
        for xmlid in server_action_xmlids:
            actions += actions.env.ref(f"hr_presence.{xmlid}")
        return actions.read(['id', 'value'])

    def _action_set_manual_presence(self, state):
        if not self.env.user.has_group('hr.group_hr_manager'):
            raise UserError(_("You don't have the right to do this. Please contact an Administrator."))
        self.write({
            'manually_set_present': state,
            'manually_set_presence': True,
            "hr_presence_state_display": 'present' if state else 'absent',
        })

    def action_set_present(self):
        self._action_set_manual_presence(True)

    def action_set_absent(self):
        self._action_set_manual_presence(False)

    def write(self, vals):
        if vals.get('hr_presence_state_display') == 'present':
            vals['manually_set_present'] = True
        return super().write(vals)

    def action_open_leave_request(self):
        if len(self) == 1:
            model = 'hr.leave'
            context = {'default_employee_id': self.id}
        else:
            model = 'hr.leave.generate.multi.wizard'
            context = {
                'default_employee_ids': self.ids,
                'default_date_from': fields.Date.today(),
                'default_date_to': fields.Date.today(),
                'default_name': _('Unplanned Absence'),
            }

        return {
            'type': 'ir.actions.act_window',
            'res_model': model,
            'views': [[False, 'form']],
            'view_mode': 'form',
            'context': context,
            'target': 'new',
        }

    # --------------------------------------------------
    # Messaging
    # --------------------------------------------------

    def action_send_sms(self):
        if not self.env.user.has_group('hr.group_hr_manager'):
            raise UserError(_("You don't have the right to do this. Please contact an Administrator."))

        context = dict(self.env.context)
        context.update(default_res_model='hr.employee', default_res_ids=self.ids, default_composition_mode='mass', default_number_field_name='mobile_phone', default_mass_keep_log=True)

        template = self.env.ref('hr_presence.sms_template_presence', False)
        if not template:
            context['default_body'] = _("""We hope this message finds you well. It has come to our attention that you are currently not present at work, and there is no record of a time off request from you. If this absence is due to an oversight on our part, we sincerely apologize for any confusion.
Please take the necessary steps to address this unplanned absence. Should you have any questions or need assistance, do not hesitate to reach out to your manager or the HR department at your earliest convenience.
Thank you for your prompt attention to this matter.""")
        else:
            context['default_template_id'] = template.id

        return {
            "type": "ir.actions.act_window",
            "res_model": "sms.composer",
            "view_mode": 'form',
            "context": context,
            "name": self.env._("Send SMS"),
            "target": "new",
        }

    def action_send_log(self):
        if not self.env.user.has_group('hr.group_hr_manager'):
            raise UserError(_("You don't have the right to do this. Please contact an Administrator."))

        for employee in self:
            employee.message_post(body=_(
                "%(name)s has been noted as %(state)s today",
                name=employee.name,
                state=employee.hr_presence_state_display))
