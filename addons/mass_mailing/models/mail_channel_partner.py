# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from email.utils import formataddr
from odoo import models, api, fields

class ChannelPartner(models.Model):
    """ Update channel partner to add blacklist fields that can be used
       to avoid sending messages from channel to the partner. """
    _name = 'mail.channel.partner'
    _inherit = ['mail.channel.partner', 'mail.mass_mailing.blacklist.mixin']

    # Override _email_field_name from the blacklist mixin
    _email_field_name = ['partner_email']


class Channel(models.Model):
    """ A mail.channel is a discussion group that may behave like a listener
    on documents. """
    _name = 'mail.channel'
    _inherit = ['mail.channel']

    # Override to implement blacklist on channel send notifications
    @api.multi
    def _notify_email_recipients(self, message, recipient_ids):
        # Excluded Blacklisted
        recipients = self.env['res.partner'].sudo().browse(recipient_ids).read(['id', 'name', 'email'])
        blacklist = self.env['mail.mass_mailing.blacklist'].sudo().search(
            [('email', 'in', [rec['email'] for rec in recipients])]).mapped('email')
        whitelist = []
        for rec in recipients:
            if rec['email'] not in blacklist:
                whitelist.append(rec)

        # real mailing list: multiple recipients (hidden by X-Forge-To)
        if self.alias_domain and self.alias_name:
            return {
                'email_to': ','.join(formataddr((partner['name'], partner['email'])) for partner in whitelist),
                'recipient_ids': [],
            }
        return super(Channel, self)._notify_email_recipients(message, [i['id'] for i in whitelist])