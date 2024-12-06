# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventRegistration(models.Model):
    _inherit = ['event.registration']

    def _show_event_on_resume(self):
        self.ensure_one()
        return (
            self.partner_id.employee_ids
            and self.state == 'done'
            and any(self.event_id.tag_ids.category_id.mapped('show_on_resume'))
        )

    def action_set_done(self):
        ret = super().action_set_done()
        resume_line_vals_list = []
        for registration in self:
            if registration._show_event_on_resume():
                resume_line_vals_list.extend([
                    registration.event_id._get_resume_line_vals(employee)
                    for employee in registration.partner_id.employee_ids
                ])
        self.env['hr.resume.line'].create(resume_line_vals_list)
        return ret
