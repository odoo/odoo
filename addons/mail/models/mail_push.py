# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailPush(models.Model):
    _name = 'mail.push'
    _description = "Push Notifications"

    mail_push_device_id = fields.Many2one('mail.push.device', string='Device', required=True, ondelete="cascade")
    payload = fields.Text()

    @api.model
    def _push_notification_to_endpoint(self, batch_size=50):
        """Send to web browser endpoint computed notification"""
        mail_push_sudo = self.sudo().search_fetch([], ['mail_push_device_id', 'payload'], limit=batch_size)
        if not mail_push_sudo:
            return

        # process send notif
        payloads = dict.fromkeys(mail_push_sudo.mail_push_device_id.ids, [])
        for push_sudo in mail_push_sudo:
            payloads[push_sudo.mail_push_device_id.id].append(push_sudo.payload)
        devices_to_unlink_sudo = mail_push_sudo.mail_push_device_id._push_to_end_point(payloads)

        # invalid credentials: no need to trigger cron again
        if devices_to_unlink_sudo is None:
            return

        # clean up notif
        mail_push_sudo.unlink()

        # clean up obsolete devices
        if devices_to_unlink_sudo:
            devices_to_unlink_sudo.unlink()

        # restart the cron if needed
        if self.search_count([]) > 0:
            self.env.ref('mail.ir_cron_web_push_notification')._trigger()
