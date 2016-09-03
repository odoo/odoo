# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, _
from odoo.tools import decode_message_header, email_split

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_route_verify(self, message, message_dict, route,
                             update_author=True, assert_model=True,
                             create_fallback=True, allow_private=False,
                             drop_alias=False):
        res = super(MailThread, self).message_route_verify(
            message, message_dict, route,
            update_author=update_author,
            assert_model=assert_model,
            create_fallback=create_fallback,
            allow_private=allow_private,
            drop_alias=drop_alias)

        if res:
            alias = route[4]
            email_from = decode_message_header(message, 'From')
            message_id = message.get('Message-Id')

            # Alias: check alias_contact settings for employees
            if alias and alias.alias_contact == 'employees':
                email_address = email_split(email_from)[0]
                employee = self.env['hr.employee'].search([('work_email', 'ilike', email_address)], limit=1)
                if not employee:
                    employee = self.env['hr.employee'].search([('user_id.email', 'ilike', email_address)], limit=1)
                if not employee:
                    mail_template = self.env.ref('hr.mail_template_data_unknown_employee_email_address')
                    self._routing_warn(_('alias %s does not accept unknown employees') % alias.alias_name, _('skipping'), message_id, route, False)
                    self._routing_create_bounce_email(email_from, mail_template.body_html, message)
                    return False
        return res
