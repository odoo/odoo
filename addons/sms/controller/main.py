# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class SmsController(http.Controller):

    @http.route('/sms/status', type='json', auth='public', csrf=False)
    def update_sms_status(self, message):
        request.env.cr.execute('''
            SELECT TRUE 
            FROM information_schema.columns 
            WHERE table_name='sms_sms' and column_name='provider_state';
        ''')

        if request.env.cr.fetchone():
            sms = request.env["sms.sms"].sudo().search([('request_id', '=', message['request_id'])])
            if sms.exists():
                sms.write({
                    'provider_state': message['provider_state']
                })
                if message['provider_state'] != 'delivered':
                    notifications = request.env['mail.notification'].sudo().search([
                            ('notification_type', '=', 'sms'),
                            ('sms_id', '=', sms.id),
                            ('notification_status', 'not in', ('canceled',))]
                        )
                    if notifications:
                        if message['provider_state'] not in  ('sent', 'delivered'):
                            notifications.write({
                                'notification_status': 'exception',
                                'failure_type': "sms_" + message['provider_state'],
                                'failure_reason': False,
                            })
                        else:
                            notifications.write({
                                'notification_status': 'sent',
                                'failure_type': False,
                                'failure_reason': False,
                            })

                    sms.mail_message_id._notify_sms_update()
                else:
                    sms.unlink()
        else:
            _logger.warning('Your database is not up to date. If you want to get feedback about your sms please update your database (sms)')
        return 'OK'
