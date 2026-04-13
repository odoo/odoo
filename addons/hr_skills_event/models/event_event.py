# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class EventEvent(models.Model):
    _inherit = 'event.event'

    @api.model_create_multi
    def create(self, vals_list):
        # TODO: Should be replaced by a boolean flag on events in master to make 'onsite' events easier to identify.
        # When creating an event considered as "onsite event" register
        # current employee as attendee of the event
        events = super().create(vals_list)
        if self.env.context.get('hr_skills_event_add_employee'):
            if employee := self.env['hr.employee'].search([('id', '=', self.env.context.get('default_employee_id')), ('work_contact_id', '!=', False)], limit=1):
                partner = employee.work_contact_id
                vals_list = []
                for event in events:
                    if partner not in event.registration_ids.partner_id:
                        vals_list.append({
                            'partner_id': partner.id,
                            'event_id': event.id,
                        })
                self.env['event.registration'].create(vals_list)
        return events
