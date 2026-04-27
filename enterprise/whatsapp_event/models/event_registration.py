# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    date_tz = fields.Selection(related='event_id.date_tz')

    def _whatsapp_get_portal_url(self):
        """ Return website_url if website_event is installed (introspect fields
        to avoid yet another bridge module) """
        self.ensure_one()
        if "website_url" in self.event_id:
            return self.event_id.website_url
        return super()._whatsapp_get_portal_url()

    def _whatsapp_get_responsible(self, related_message=False, related_record=False, whatsapp_account=False):
        if self.event_user_id:
            return self.event_user_id

        return super()._whatsapp_get_responsible(related_message, related_record, whatsapp_account)

    def _get_whatsapp_safe_fields(self):
        return {'name', 'event_id.name', 'event_id.organizer_id.name', 'event_date_range', 'event_id.user_id.name',
                'event_id.user_id.mobile', 'event_id.address_id.city', 'event_id.address_id.name',
                'event_id.address_id.contact_address_complete', 'event_id.address_id.partner_latitude',
                'event_id.address_id.partner_longitude'}
