# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import models, _
from odoo.tools import html2plaintext


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def execute_command_lead(self, **kwargs):
        key = kwargs['body']
        lead_command = "/lead"
        if key.strip() == lead_command:
            msg = _(
                "Create a new lead: "
                "%(pre_start)s%(lead_command)s %(i_start)slead title%(i_end)s%(pre_end)s",
                lead_command=lead_command,
                pre_start=Markup("<pre>"),
                pre_end=Markup("</pre>"),
                i_start=Markup("<i>"),
                i_end=Markup("</i>"),
            )
        else:
            lead = self._convert_visitor_to_lead(self.env.user.partner_id, key)
            msg = _("Created a new lead: %s", lead._get_html_link())
        self.env.user._bus_send_transient_message(self, msg)

    def _get_crm_lead_vals(self, partner, key, customers):
        return {
            'name': html2plaintext(key[5:]),
            'partner_id': customers[0].id if customers else False,
            'user_id': False,
            'team_id': False,
            'description': self._get_channel_history(),
            'referred': partner.name,
        }

    def _convert_visitor_to_lead(self, partner, key):
        """ Create a lead from channel /lead command
        :param partner: internal user partner (operator) that created the lead;
        :param key: operator input in chat ('/lead Lead about Product')
        """
        # if public user is part of the chat: consider lead to be linked to an
        # anonymous user whatever the participants. Otherwise keep only share
        # partners (no user or portal user) to link to the lead.
        customers = self.env['res.partner']
        for customer in self.with_context(active_test=False).channel_partner_ids.filtered(lambda p: p != partner and p.partner_share):
            if customer.is_public:
                customers = self.env['res.partner']
                break
            else:
                customers |= customer

        lead_vals = self._get_crm_lead_vals(partner, key, customers)
        lead = None
        if lead_vals:
            lead = self.env['crm.lead'].create(lead_vals)
        return lead
