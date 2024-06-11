# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class IapAccount(models.Model):
    _inherit = 'iap.account'

    @api.model
    def _send_success_notification(self, message, title=None):
        self._send_status_notification(message, 'success', title=title)

    @api.model
    def _send_error_notification(self, message, title=None):
        self._send_status_notification(message, 'danger', title=title)

    @api.model
    def _send_status_notification(self, message, status, title=None):
        params = {
            'message': message,
            'type': status,
        }

        if title is not None:
            params['title'] = title

        self.env['bus.bus']._sendone(self.env.user.partner_id, 'iap_notification', params)

    @api.model
    def _send_no_credit_notification(self, service_name, title):
        params = {
            'title': title,
            'type': 'no_credit',
            'get_credits_url': self.env['iap.account'].get_credits_url(service_name),
        }
        self.env['bus.bus']._sendone(self.env.user.partner_id, 'iap_notification', params)
