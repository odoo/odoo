# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, models


class ScheduledMessage(models.Model):
    _inherit = 'mail.scheduled.message'

    def _post_message(self, raise_exception=True):
        order_messages = self.env['mail.scheduled.message'].with_context(mark_so_as_sent=True)
        for scheduled_message in self:
            notification_parameters = json.loads(scheduled_message.notification_parameters or '{}')
            if 'mark_so_as_sent' not in notification_parameters:
                continue
            if notification_parameters.pop('mark_so_as_sent'):
                order_messages += scheduled_message
            scheduled_message.notification_parameters = json.dumps(notification_parameters)
        if order_messages:
            super(ScheduledMessage, order_messages)._post_message(raise_exception=raise_exception)
        if remaining := self - order_messages:
            super(ScheduledMessage, remaining)._post_message(raise_exception=raise_exception)

    @api.model
    def _notification_parameters_whitelist(self):
        return super()._notification_parameters_whitelist() | {'mark_so_as_sent'}
