# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools import html2plaintext, html_escape


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
            lead = self._convert_visitor_to_lead(partner, channel_partners, key)
            msg = _('Created a new lead: <a href="#" data-oe-id="%s" data-oe-model="crm.lead">%s</a>') % (lead.id, html_escape(lead.name))
        self._send_transient_message(partner, msg)

    def _convert_visitor_to_lead(self, partner, channel_partners, key):
        """ Create a lead from channel /lead command
        :param partner: internal user partner (operator) that created the lead;
        :param channel_partners: channel members;
        :param key: operator input in chat ('/lead Lead about Product')
        """
        description = ''.join(
            '%s: %s\n' % (message.author_id.name or self.anonymous_name, message.body)
            for message in self.channel_message_ids.sorted('id')
        )
        # if public user is part of the chat: consider lead to be linked to an
        # anonymous user whatever the participants. Otherwise keep only share
        # partners (no user or portal user) to link to the lead.
        customers = self.env['res.partner']
        for customer in channel_partners.partner_id.filtered('partner_share'):
            if customer.user_ids and all(user._is_public() for user in customer.user_ids):
                customers = self.env['res.partner']
                break
            else:
                customers |= customer

        utm_source = self.env.ref('crm_livechat.utm_source_livechat', raise_if_not_found=False)
        return self.env['crm.lead'].create({
            'name': html2plaintext(key[5:]),
            'partner_id': customers[0].id if customers else False,
            'user_id': False,
            'team_id': False,
            'description': html2plaintext(description),
            'referred': partner.name,
            'source_id': utm_source and utm_source.id,
        })
