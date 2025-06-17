# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    @api.model_create_multi
    def create(self, vals_list):
        new_registrations = super().create(vals_list)
        new_registrations._create_resume_lines()
        return new_registrations

    def write(self, vals):
        result = super().write(vals)
        self._create_resume_lines()
        return result

    def _create_resume_lines(self):
        ResumeLine = self.env['hr.resume.line']
        resume_line_vals_list = []
        registrations_by_event = self.filtered(lambda r: r.state == 'done').grouped('event_id')
        for event, registrations in registrations_by_event.items():
            if not event.tag_ids.category_id.hr_resume_line_type_id:
                continue

            resume_line_vals_list.extend([{
                    **ResumeLine._values_from_event(event),
                    'employee_id': employee.id,
                }
                for employee in registrations.partner_id.sudo().employee_ids
                if event not in employee.resume_line_ids.event_id
            ])
        ResumeLine.sudo().create(resume_line_vals_list)
