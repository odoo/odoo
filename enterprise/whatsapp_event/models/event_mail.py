# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    notification_type = fields.Selection(selection_add=[('whatsapp', 'WhatsApp')])
    template_ref = fields.Reference(ondelete={'whatsapp.template': 'cascade'}, selection_add=[('whatsapp.template', 'WhatsApp')])

    @api.constrains('template_ref')
    def _check_whatsapp_template_phone_field(self):
        for record in self:
            if record.notification_type == 'whatsapp' and not record.template_ref.phone_field:
                raise ValidationError(_('Whatsapp Templates in Events must have a phone field set.'))

    def _compute_notification_type(self):
        super()._compute_notification_type()
        social_schedulers = self.filtered(lambda scheduler: scheduler.template_ref and scheduler.template_ref._name == 'whatsapp.template')
        social_schedulers.notification_type = 'whatsapp'

    def _execute_event_based_for_registrations(self, registrations):
        if self.notification_type == "whatsapp":
            self._send_whatsapp(registrations)
        return super()._execute_event_based_for_registrations(registrations)

    def _filter_template_ref(self):
        valid = super()._filter_template_ref()
        invalid = valid.filtered(
            lambda scheduler: scheduler.notification_type == "whatsapp" and scheduler.template_ref.status != "approved"
        )
        for scheduler in invalid:
            _logger.warning(
                "Cannot process scheduler %s (event %s - ID %s) as it refers to whatsapp template %s (ID %s) that is not approved",
                scheduler.id, scheduler.event_id.name, scheduler.event_id.id,
                scheduler.template_ref.name, scheduler.template_ref.id)
        return valid - invalid

    def _template_model_by_notification_type(self):
        info = super()._template_model_by_notification_type()
        info["whatsapp"] = "whatsapp.template"
        return info

    def _filter_wa_template_ref(self):
        """ Check for valid template reference: existing, working template """
        return self._filter_template_ref()

    def _send_whatsapp(self, registrations):
        """ Whatsapp action: send whatsapp to attendees """
        self.env['whatsapp.composer'].with_context(
            {'active_ids': registrations.ids}
        ).create({
            'res_model': 'event.registration',
            'wa_template_id': self.template_ref.id
        })._send_whatsapp_template(force_send_by_cron=True)
