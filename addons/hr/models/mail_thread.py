# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models
from odoo.addons.mail.models.mail_thread import decode_header
from odoo.tools import email_split

_logger = logging.getLogger(__name__)

class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_route_verify(self, message, message_dict, route, update_author=True, assert_model=True, create_fallback=True, allow_private=False):
        res = super(MailThread, self).message_route_verify(message, message_dict, route, update_author, assert_model, create_fallback, allow_private)

        if res:
            alias = route[4]
            email_from = decode_header(message, 'From')
            message_id = message.get('Message-Id')

            # Identically equal to the definition in mail module because sub methods are local
            # variables and cannot be called with super
            def _create_bounce_email(body_html):
                bounce_to = decode_header(message, 'Return-Path') or email_from
                bounce_mail_values = {
                    'body_html': body_html,
                    'subject': 'Re: %s' % message.get('subject'),
                    'email_to': bounce_to,
                    'auto_delete': True,
                }
                bounce_from = self.env['ir.mail_server']._get_default_bounce_address()
                if bounce_from:
                    bounce_mail_values['email_from'] = 'MAILER-DAEMON <%s>' % bounce_from
                self.env['mail.mail'].create(bounce_mail_values).send()

            def _warn(message):
                _logger.info('Routing mail with Message-Id %s: route %s: %s',
                             message_id, route, message)

            # Alias: check alias_contact settings for employees

            if alias and alias.alias_contact == 'employees':
                email_address = email_split(email_from)[0]
                employee = self.env['hr.employee'].search([('work_email', 'ilike', email_address)], limit=1)
                if not employee:
                    employee = self.env['hr.employee'].search([('user_id.email', 'ilike', email_address)], limit=1)
                if not employee:
                    mail_template = self.env.ref('hr.mail_template_data_unknown_employee_email_address')
                    _warn('alias %s does not accept unknown employees, skipping' % alias.alias_name)
                    _create_bounce_email(mail_template.body_html)
                    return False
        return res
