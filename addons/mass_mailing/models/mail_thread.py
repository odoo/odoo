# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import datetime

from odoo import api, models, tools, fields
from odoo.tools import decode_smtp_header, decode_message_header

_logger = logging.getLogger(__name__)
BLACKLIST_MAX_BOUNCED_LIMIT = 5


class MailThread(models.AbstractModel):
    """ Update MailThread to add the support of bounce management in mass mailing statistics. """
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """ Override to udpate mass mailing statistics based on bounce emails """
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param("mail.bounce.alias")
        email_to = decode_message_header(message, 'To')
        email_to_localparts = [
            e.split('@', 1)[0].lower()
            for e in (tools.email_split(email_to) or [''])
        ]

        if bounce_alias and any(email.startswith(bounce_alias) for email in email_to_localparts):
            bounce_re = re.compile("%s\+(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)
            if bounce_match:
                bounced_mail_id = bounce_match.group(1)
                self.env['mail.mail.statistics'].set_bounced(mail_mail_ids=[bounced_mail_id])

        return super(MailThread, self).message_route(message, message_dict, model, thread_id, custom_values)

    @api.model
    def message_route_process(self, message, message_dict, routes):
        """ Override to update the parent mail statistics. The parent is found
        by using the References header of the incoming message and looking for
        matching message_id in mail.mail.statistics. """
        if routes:
            references = tools.decode_message_header(message, 'References')
            in_reply_to = tools.decode_message_header(message, 'In-Reply-To').strip()
            thread_references = references or in_reply_to
            # even if 'reply_to' in ref (cfr mail/mail_thread) that indicates a new thread redirection
            # (aka bypass alias configuration in gateway) consider it as a reply for statistics purpose
            references_msg_id_list = tools.mail_header_msgid_re.findall(thread_references)

            if references_msg_id_list:
                self.env['mail.mail.statistics'].set_opened(mail_message_ids=references_msg_id_list)
                self.env['mail.mail.statistics'].set_replied(mail_message_ids=references_msg_id_list)
        return super(MailThread, self).message_route_process(message, message_dict, routes)

    @api.multi
    def message_post_with_template(self, template_id, **kwargs):
        # avoid having message send through `message_post*` methods being implicitly considered as
        # mass-mailing
        no_massmail = self.with_context(
            default_mass_mailing_name=False,
            default_mass_mailing_id=False,
        )
        return super(MailThread, no_massmail).message_post_with_template(template_id, **kwargs)

    @api.multi
    def message_receive_bounce(self, email, partner, mail_id=None):
        """In addition, an auto blacklist rule check if the email can be blacklisted
        to avoid sending mails indefinitely to this email address.
        This rule checks if the email bounced too much. If this is the case,
        the email address is added to the blacklist in order to avoid continuing
        to send mass_mail to that email address. If it bounced too much times
        in the last month and the bounced are at least separated by one week,
        to avoid blacklist someone because of a temporary mail server error,
        then the email is considered as invalid and is blacklisted."""
        super(MailThread, self).message_receive_bounce(email, partner, mail_id=None)

        three_months_ago = fields.Datetime.to_string(datetime.datetime.now() - datetime.timedelta(weeks=13))
        stats = self.env['mail.mail.statistics'] \
            .search(['&', ('bounced', '>', three_months_ago), ('email', '=ilike', email)]) \
            .mapped('bounced')
        if len(stats) >= BLACKLIST_MAX_BOUNCED_LIMIT:
            if max(stats) > min(stats) + datetime.timedelta(weeks=1):
                blacklist_rec = self.env['mail.blacklist'].sudo()._add(email)
                blacklist_rec._message_log(
                    'This email has been automatically blacklisted because of too much bounced.')
