# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import models, fields

_logger = logging.getLogger(__name__)


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def execute(self):
        now = fields.Datetime.now()
        todo = self.filtered(lambda registration:
            not registration.mail_sent and \
            registration.registration_id.state in ['open', 'done'] and \
            (registration.scheduled_date and registration.scheduled_date <= now) and \
            registration.scheduler_id.notification_type == 'whatsapp'
        )
        # Exclude schedulers linked to invalid/unusable templates
        valid = todo.scheduler_id._filter_wa_template_ref()

        # Group todo by templates so if one tempalte then we can send in one shot
        tosend_by_template = defaultdict(list)
        for registration in todo.filtered(lambda r: r.scheduler_id in valid):
            tosend_by_template.setdefault(registration.scheduler_id.template_ref.id, [])
            tosend_by_template[registration.scheduler_id.template_ref.id].append(registration.registration_id.id)
        # Create whatsapp composer and send message by cron
        failed_registration_ids = []
        for wa_template_id, registration_ids in tosend_by_template.items():
            try:
                self.env['whatsapp.composer'].with_context({
                    'active_ids': registration_ids,
                    'active_model': 'event.registration',
                }).create({
                    'wa_template_id': wa_template_id,
                })._send_whatsapp_template(force_send_by_cron=True)
            except Exception as e:  # noqa: BLE001 we should never raise and rollback here
                _logger.warning('An issue happened when sending WhatsApp template ID %s. Received error %s', wa_template_id, e)
                failed_registration_ids += registration_ids

        # mark as sent only if really sent
        todo.filtered(
            lambda reg: reg.scheduler_id in valid and reg.registration_id.id not in failed_registration_ids
        ).mail_sent = True
        return super().execute()
