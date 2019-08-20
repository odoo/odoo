# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, models, fields
from odoo.tools import decode_smtp_header

BLACKLIST_MAX_BOUNCED_LIMIT = 5


class MailThread(models.AbstractModel):
    """ Update MailThread to add the support of bounce management in mass mailing traces. """
    _inherit = 'mail.thread'

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        """ Override to update the parent mailing traces. The parent is found
        by using the References header of the incoming message and looking for
        matching message_id in mailing.trace. """
        if message.get('References') and routes:
            message_ids = [x.strip() for x in decode_smtp_header(message['References']).split()]
            self.env['mailing.trace'].set_opened(mail_message_ids=message_ids)
            self.env['mailing.trace'].set_replied(mail_message_ids=message_ids)
        return super(MailThread, self)._message_route_process(message, message_dict, routes)

    def message_post_with_template(self, template_id, **kwargs):
        # avoid having message send through `message_post*` methods being implicitly considered as
        # mass-mailing
        no_massmail = self.with_context(
            default_mass_mailing_name=False,
            default_mass_mailing_id=False,
        )
        return super(MailThread, no_massmail).message_post_with_template(template_id, **kwargs)

    @api.model
    def _routing_handle_bounce(self, email_message, message_dict):
        """ In addition, an auto blacklist rule check if the email can be blacklisted
        to avoid sending mails indefinitely to this email address.
        This rule checks if the email bounced too much. If this is the case,
        the email address is added to the blacklist in order to avoid continuing
        to send mass_mail to that email address. If it bounced too much times
        in the last month and the bounced are at least separated by one week,
        to avoid blacklist someone because of a temporary mail server error,
        then the email is considered as invalid and is blacklisted."""
        super(MailThread, self)._routing_handle_bounce(email_message, message_dict)

        bounced_email = message_dict['bounced_email']
        bounced_msg_id = message_dict['bounced_msg_id']
        bounced_partner = message_dict['bounced_partner']

        if bounced_msg_id:
            self.env['mailing.trace'].set_bounced(mail_message_ids=[bounced_msg_id])
        if bounced_email:
            three_months_ago = fields.Datetime.to_string(datetime.datetime.now() - datetime.timedelta(weeks=13))
            stats = self.env['mailing.trace'].search(['&', ('bounced', '>', three_months_ago), ('email', '=ilike', bounced_email)]).mapped('bounced')
            if len(stats) >= BLACKLIST_MAX_BOUNCED_LIMIT and (not bounced_partner or bounced_partner.message_bounce >= BLACKLIST_MAX_BOUNCED_LIMIT):
                if max(stats) > min(stats) + datetime.timedelta(weeks=1):
                    blacklist_rec = self.env['mail.blacklist'].sudo()._add(bounced_email)
                    blacklist_rec._message_log(
                        body='This email has been automatically blacklisted because of too much bounced.')
