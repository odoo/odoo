# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError

class HrResumeLine(models.Model):
    _inherit = 'hr.resume.line'

    display_type = fields.Selection(selection_add=[('event', 'Event')])
    event_registration_id = fields.Many2one('event.registration', ondelete='cascade')
    event_id = fields.Many2one(
        'event.event', string="Event",
        domain = [('tag_ids.category_id', 'any', [('show_on_resume', '=', 'True')])],
    )

    def _create_event_registrations(self):
        registrations_vals_list = []
        for line in self:
            if not line.event_id:
                continue
            if employee_registrations := line.event_id.registration_ids.filtered(
                lambda reg: line.employee_id in reg.partner_id.employee_ids
            ):
                employee_registrations.write({'state': 'done'})
                continue
            registrations_vals_list.append({
                'state': 'done',
                'partner_id': line.employee_id.work_contact_id.id,
                'event_id': line.event_id.id,
                'resume_line_ids': [Command.link(line.id)],
            })
        
        if registrations_vals_list:
            self.env['event.registration'].sudo().with_context(no_create_resume_lines=True).create(registrations_vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._create_event_registrations()
        return lines

    def write(self, vals):
        if 'event_id' in vals:
            for line in self:
                if line.event_registration_id and line.event_registration_id.id != vals['event_id']:
                    raise UserError(_(
                        "Cannot change the event on resume line: %(line_name)s\n"
                        "because it is linked to a registration for the event: %(event_name)s\n",
                        line_name=line.name,
                        event_name=line.event_registration_id.event_id.name,
                    ))

        ret = super().write(vals)
        self._create_event_registrations()
        return ret

    def unlink(self):
        lines_by_registration = self.grouped('event_registration_id')
        for registration, unlinked_lines in lines_by_registration.items():
            if not registration:
                continue
            if registration._show_on_resume() and unlinked_lines == registration.resume_line_ids:
                registration.action_cancel()
        return super().unlink()

    @api.onchange('event_id')
    def _onchange_event_id(self):
        self.date_start = self.event_id.date_begin
        self.date_end = self.event_id.date_end
        self.name = self.event_id.name
        self.description = self.event_id.description
