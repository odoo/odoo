# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class SmsController(http.Controller):

    @http.route('/sms/status', type='json', auth='public', csrf=False)
    def update_sms_status(self, message_statuses):
        """
        Receive a batch of delivery reports from IAP

        :param message_statuses:
        [
            {
                'sms_status': status0,
                'uuids': [uuid00, uuid01, ...],
            },
            {
                'sms_status': status1,
                'uuids': [uuid10, uuid11, ...],
            },
            ...
        ]
        """
        for message_status in message_statuses:
            request.env['sms.sms'].sudo().search([
                ('uuid', 'in', message_status['uuids']),
            ]).update_status(message_status['sms_status'])
        return 'OK'
