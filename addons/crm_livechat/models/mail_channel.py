# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools import html2plaintext

class MailChannel(models.Model):
    _inherit = 'mail.channel'

    def _define_command_lead(self):
        return {'help': _('Create a new lead (/lead lead title)')}

    def _execute_command_lead(self, **kwargs):
        partner = self.env.user.partner_id
        key = kwargs['body']
        channel_partners = self.env['mail.channel.partner'].search([
            ('partner_id', '!=', partner.id),
            ('channel_id', '=', self.id)], limit=1
        )
        if key.strip() == '/lead':
            msg = self._define_command_lead()['help']
        else:
            description = ''.join(
                '%s: %s\n' % (message.author_id.name or self.anonymous_name, message.body)
                for message in self.channel_message_ids.sorted('id')
            )
            lead = self.env['crm.lead'].create({
                'name': html2plaintext(key[5:]),
                'partner_id': channel_partners.partner_id.id,
                'user_id': None,
                'team_id': None,
                'description': html2plaintext(description),
                'referred': partner.name
            })
            lead._onchange_partner_id()
            msg = _('Created a new lead: <a href="#" data-oe-id="%s" data-oe-model="crm.lead">%s</a>') % (lead.id, lead.name)
        self._send_transient_message(partner, msg)
