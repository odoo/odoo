# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    resume_line_ids = fields.One2many('hr.resume.line', 'event_registration_id', compute='_compute_resume_line_ids', store=True)

    def _show_on_resume(self):
        self.ensure_one()
        return (
            self.state == 'done'
            and any(self.event_id.tag_ids.category_id.resume_line_type_id)
        )

    def _regenerate_resume_lines(self):
        create_vals_list = []
        lines_to_unlink = self.env['hr.resume.line']

        def line_vals(registration, employee, line_type):
            return {
                'employee_id': employee.id,
                'event_registration_id': registration.id,
                'event_id': registration.event_id.id,
                'name': registration.event_id.name,
                'date_start': registration.event_id.date_begin,
                'date_end': registration.event_id.date_end,
                'line_type_id': line_type.id,
            }

        for registration in self:

            if not registration._show_on_resume():
                lines_to_unlink |= registration.resume_line_ids
                continue
            lines_to_unlink |= registration.resume_line_ids.filtered(
                lambda line: line.employee_id not in registration.partner_id.employee_ids
            )

            if self.env.context.get('no_create_resume_lines'):
                continue
            line_type = self.event_id.tag_ids.category_id.resume_line_type_id[0]
            create_vals_list.extend([
                line_vals(registration, employee, line_type)
                for employee in registration.partner_id.employee_ids
                if employee not in registration.resume_line_ids.employee_id
            ])

        lines_to_unlink.unlink()
        if create_vals_list:
            self.env['hr.resume.line'].create(create_vals_list)

    @api.depends('partner_id.employee_ids', 'event_id.tag_ids.category_id.resume_line_type_id')
    def _compute_resume_line_ids(self):
        self._regenerate_resume_lines()

    def write(self, vals):
        ret = super().write(vals)
        if vals.get('state') == 'done':
            self._regenerate_resume_lines()
        elif 'state' in vals:
            self.resume_line_ids.unlink()
        return ret

    @api.model_create_multi
    def create(self, vals_list):
        registrations = super().create(vals_list)
        if registrations_needing_lines := registrations.filtered(lambda reg: reg.state == 'done'):
            registrations_needing_lines._regenerate_resume_lines()
        return registrations
