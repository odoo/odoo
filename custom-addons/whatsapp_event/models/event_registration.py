# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    date_range = fields.Char("Date Range", compute='_compute_date_range')

    @api.depends('event_begin_date')
    @api.depends_context('uid')
    def _compute_date_range(self):
        for registration in self:
            lang_code = registration.partner_id.lang or self.env.user.lang
            registration.date_range = registration.get_date_range_str(lang_code=lang_code)

    def _whatsapp_get_portal_url(self):
        self.ensure_one()
        return self.event_id.website_url

    def _whatsapp_get_responsible(self, related_message=False, related_record=False, whatsapp_account=False):
        if self.event_user_id:
            return self.event_user_id

        return super()._whatsapp_get_responsible(related_message, related_record, whatsapp_account)

    def _get_whatsapp_safe_fields(self):
        return {'name', 'event_id.name', 'event_id.organizer_id.name', 'date_range', 'event_id.user_id.name',
                'event_id.user_id.mobile', 'event_id.address_id.city', 'event_id.address_id.name',
                'event_id.address_id.contact_address_complete', 'event_id.address_id.partner_latitude',
                'event_id.address_id.partner_longitude'}

    def _whatsapp_get_timezone(self):
        if self:
            self.ensure_one()
            return self.event_id.date_tz
        return super()._whatsapp_get_timezone()
