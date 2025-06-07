# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def _do_sms_reminder(self, alarms):
        """ Send an SMS text reminder to attendees that haven't declined the event """
        for event in self:
            declined_partners = event.attendee_ids.filtered_domain([('state', '=', 'declined')]).partner_id
            for alarm in alarms:
                partners = event._mail_get_partners()[event.id].filtered(
                    lambda partner: partner.phone_sanitized and partner not in declined_partners
                )
                if event.user_id and not alarm.sms_notify_responsible:
                    partners -= event.user_id.partner_id
                event._message_sms_with_template(
                    template=alarm.sms_template_id,
                    template_fallback=_("Event reminder: %(name)s, %(time)s.", name=event.name, time=event.display_time),
                    partner_ids=partners.ids,
                    put_in_queue=False
                )

    def action_send_sms(self):
        if not self.partner_ids:
            raise UserError(_("There are no attendees on these events"))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Send SMS"),
            'res_model': 'sms.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_composition_mode': 'mass',
                'default_res_model': 'res.partner',
                'default_res_ids': self.partner_ids.ids,
                'default_mass_keep_log': True,
            },
        }

    def _get_trigger_alarm_types(self):
        return super()._get_trigger_alarm_types() + ['sms']
