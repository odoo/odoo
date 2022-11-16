# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from markupsafe import Markup

from odoo import api, models, fields, tools, _

BLACKLIST_MAX_BOUNCED_LIMIT = 5


class MailThread(models.AbstractModel):
    """ Update MailThread to add the support of bounce management in mass mailing traces. """
    _inherit = 'mail.thread'

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        """ Override to update the parent mailing traces. The parent is found
        by using the References header of the incoming message and looking for
        matching message_id in mailing.trace. """
        if routes:
            # even if 'reply_to' in ref (cfr mail/mail_thread) that indicates a new thread redirection
            # (aka bypass alias configuration in gateway) consider it as a reply for statistics purpose
            thread_references = message_dict['references'] or message_dict['in_reply_to']
            msg_references = tools.mail_header_msgid_re.findall(thread_references)
            if msg_references:
                self.env['mailing.trace'].set_opened(domain=[('message_id', 'in', msg_references)])
                self.env['mailing.trace'].set_replied(domain=[('message_id', 'in', msg_references)])
        return super(MailThread, self)._message_route_process(message, message_dict, routes)

    def message_mail_with_source(self, source_ref, **kwargs):
        # avoid having message send through `message_post*` methods being implicitly considered as
        # mass-mailing
        return super(MailThread, self.with_context(
            default_mass_mailing_name=False,
            default_mass_mailing_id=False,
        )).message_mail_with_source(source_ref, **kwargs)

    def message_post_with_source(self, source_ref, **kwargs):
        # avoid having message send through `message_post*` methods being implicitly considered as
        # mass-mailing
        return super(MailThread, self.with_context(
            default_mass_mailing_name=False,
            default_mass_mailing_id=False,
        )).message_post_with_source(source_ref, **kwargs)

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
        bounced_msg_ids = message_dict['bounced_msg_ids']
        bounced_partner = message_dict['bounced_partner']

        if bounced_msg_ids:
            self.env['mailing.trace'].set_bounced(
                domain=[('message_id', 'in', bounced_msg_ids)],
                bounce_message=tools.html2plaintext(message_dict.get('body') or ''))
        if bounced_email:
            three_months_ago = fields.Datetime.to_string(datetime.datetime.now() - datetime.timedelta(weeks=13))
            stats = self.env['mailing.trace'].search(['&', '&', ('trace_status', '=', 'bounce'), ('write_date', '>', three_months_ago), ('email', '=ilike', bounced_email)]).mapped('write_date')
            if len(stats) >= BLACKLIST_MAX_BOUNCED_LIMIT and (not bounced_partner or any(p.message_bounce >= BLACKLIST_MAX_BOUNCED_LIMIT for p in bounced_partner)):
                if max(stats) > min(stats) + datetime.timedelta(weeks=1):
                    self.env['mail.blacklist'].sudo()._add(
                        bounced_email,
                        message=Markup('<p>%s</p>') % _('This email has been automatically added in blocklist because of too much bounced.')
                    )

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        defaults = {}

        if issubclass(type(self), self.pool['utm.mixin']):
            thread_references = msg_dict.get('references', '') or msg_dict.get('in_reply_to', '')
            msg_references = tools.mail_header_msgid_re.findall(thread_references)
            if msg_references:
                traces = self.env['mailing.trace'].search([('message_id', 'in', msg_references)], limit=1)
                if traces:
                    defaults['campaign_id'] = traces.campaign_id.id
                    defaults['source_id'] = traces.mass_mailing_id.source_id.id
                    defaults['medium_id'] = traces.mass_mailing_id.medium_id.id

        if custom_values:
            defaults.update(custom_values)

        return super(MailThread, self).message_new(msg_dict, custom_values=defaults)
