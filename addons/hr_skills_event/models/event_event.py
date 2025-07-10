# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventEvent(models.Model):
    _inherit = 'event.event'

    has_employees_registered = fields.Boolean(compute='_compute_has_employees_registered', store=True)

    @api.depends('registration_ids')
    def _compute_has_employees_registered(self):
        employee_partners = self.env['hr.employee'].search([]).mapped('work_contact_id')
        for event in self:
            event.has_employees_registered = any(
                partner in employee_partners for partner in event.registration_ids.partner_id
            )
