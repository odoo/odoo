# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    visitor_id = fields.Many2one('website.visitor', string='Visitor', ondelete='set null', index='btree_not_null')

    def _get_website_registration_allowed_fields(self):
        return {'name', 'phone', 'email', 'company_name', 'event_id', 'partner_id', 'event_slot_id', 'event_ticket_id'}

    def get_base_url(self):
        if self.event_id:
            return self.event_id.get_base_url()
        return super().get_base_url()
