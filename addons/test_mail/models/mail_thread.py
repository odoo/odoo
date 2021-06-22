# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, tools

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_process_check(self, message, message_dict):
        if self.env.context.get('test_mail_skip_custom_gateway', True):
            # do not degrade perf and behavior except some specific tests
            return super(MailThread, self)._message_process_check(message, message_dict)

        existing_msg_ids = self.env['mail.gateway.message'].search([('message_id', '=', message_dict['message_id'])], limit=1)
        if existing_msg_ids:
            _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                         message_dict.get('email_from'), message_dict.get('to'), message_dict.get('message_id'))
            return False
        return super(MailThread, self)._message_process_check(message, message_dict)

    def message_parse(self, message, save_original=False):
        if self.env.context.get('test_mail_skip_custom_gateway', True):
            # do not degrade perf and behavior except some specific tests
            return super(MailThread, self).message_parse(message, save_original=save_original)

        msg_dict = super(MailThread, self).message_parse(message, save_original=save_original)
        parent_ids = False
        if msg_dict['in_reply_to']:
            parent_ids = self.env['mail.gateway.message'].search([('message_id', '=', msg_dict['in_reply_to'])], limit=1)
        if msg_dict['references'] and not parent_ids:
            references_msg_id_list = tools.mail_header_msgid_re.findall(msg_dict['references'])
            parent_ids = self.env['mail.gateway.message'].search([('message_id', 'in', [x.strip() for x in references_msg_id_list])], limit=1)
        msg_dict['parent_id'] = parent_ids.id if parent_ids else False
        msg_dict['is_internal'] = False  # do not handle internal flag (probably remove actually)
        return msg_dict

    def _message_parse_extract_bounce(self, message, message_dict):
        if self.env.context.get('test_mail_skip_custom_gateway', True):
            # do not degrade perf and behavior except some specific tests
            return super(MailThread, self)._message_parse_extract_bounce(message, message_dict)

        bounce_info = super(MailThread, self)._message_parse_extract_bounce(message, message_dict)
        if bounce_info['bounced_msg_id']:
            bounce_info['bounced_custom_message'] = self.env['mail.gateway.message'].sudo().search([
                ('message_id', 'in', bounce_info['bounced_msg_id'])
            ])
        else:
            bounce_info['bounced_custom_message'] = self.env['mail.gateway.message'].sudo()
        return bounce_info
