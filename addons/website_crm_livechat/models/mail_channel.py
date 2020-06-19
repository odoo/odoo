# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    def _convert_visitor_to_lead(self, partner, channel_partners, key):
        """ When website is installed, we can link the created lead from /lead command
         to the current website_visitor. We do not use the lead name as it does not correspond
         to the lead contact name."""
        lead = super(MailChannel, self)._convert_visitor_to_lead(partner, channel_partners, key)
        visitor_sudo = self.livechat_visitor_id.sudo()
        if visitor_sudo:
            visitor_sudo.write({'lead_ids': [(4, lead.id)]})
        return lead
