# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrResumeLine(models.Model):
    _inherit = ['hr.resume.line']

    event_id = fields.Many2one('event.event', string="Event", domain=[('is_finished', '=', True)])

    @api.model
    def get_event_type_id(self):
        return self.env.ref('event_hr_skills.resume_type_events').id

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        registrations_vals_list = []
        for line in lines:
            if not line.event_id:
                continue
            if line.employee_id in line.event_id.registration_ids.partner_id.employee_ids:
                continue
            registrations_vals_list.append({
                'state': 'done',
                'partner_id': line.employee_id.work_contact_id.id,
                'event_id': line.event_id.id,
            })
        self.env['event.registration'].sudo().create(registrations_vals_list)
        return lines

    @api.onchange('event_id')
    def _onchange_event_id(self):
        self.date_start = self.event_id.date_begin
        self.date_end = self.event_id.date_end
        self.name = self.event_id.name

