# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from requests import Session

from odoo import api, fields, models
from odoo.addons.mail.tools.web_push import push_to_end_point, DeviceUnreachableError

_logger = logging.getLogger(__name__)


class MailPush(models.Model):
    _name = 'mail.push'
    _description = "Push Notifications"

    mail_push_device_id = fields.Many2one('mail.push.device', string='devices', required=True, ondelete="cascade")
    payload = fields.Text()

    @api.model
    def _push_notification_to_endpoint(self, batch_size=50):
        """Send to web browser endpoint computed notification"""
        web_push_notifications_sudo = self.sudo().search_fetch([], ['mail_push_device_id', 'payload'], limit=batch_size)
        if not web_push_notifications_sudo:
            return

        ir_parameter_sudo = self.env['ir.config_parameter'].sudo()
        vapid_private_key = ir_parameter_sudo.get_param('mail.web_push_vapid_private_key')
        vapid_public_key = ir_parameter_sudo.get_param('mail.web_push_vapid_public_key')
        if not vapid_private_key or not vapid_public_key:
            return

        session = Session()
        devices_to_unlink = set()

        # process send notif
        devices = web_push_notifications_sudo.mail_push_device_id.grouped('id')
        for web_push_notification_sudo in web_push_notifications_sudo:
            device = devices.get(web_push_notification_sudo.mail_push_device_id.id)
            if device.id in devices_to_unlink:
                continue
            try:
                push_to_end_point(
                    base_url=self.get_base_url(),
                    device={
                        'id': device.id,
                        'endpoint': device.endpoint,
                        'keys': device.keys
                    },
                    payload=web_push_notification_sudo.payload,
                    vapid_private_key=vapid_private_key,
                    vapid_public_key=vapid_public_key,
                    session=session,
                )
            except DeviceUnreachableError:
                devices_to_unlink.add(device.id)

        # clean up notif
        web_push_notifications_sudo.unlink()

        # clean up obsolete devices
        if devices_to_unlink:
            self.env['mail.push.device'].sudo().browse(devices_to_unlink).unlink()

        # restart the cron if needed
        if self.search_count([]) > 0:
            self.env.ref('mail.ir_cron_web_push_notification')._trigger()
