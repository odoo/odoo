from odoo import models, _
from odoo.tools import html2plaintext


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

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

    def _get_crm_lead_vals(self, partner, key, customers):
        return {
            'name': html2plaintext(key[5:]),
            'partner_id': customers[0].id if customers else False,
            'user_id': False,
            'team_id': False,
            'description': self._get_channel_history(),
            'referred': partner.name,
        }

    def execute_command_lead(self, **kwargs):
        partner = self.env.user.partner_id
        key = kwargs['body']
        if key.strip() == '/lead':
            msg = _('Create a new lead (/lead lead title)')
        else:
            lead = self._convert_visitor_to_lead(partner, key)
            if lead:
                msg = _('Created a new lead: %s', lead._get_html_link())
            else:
                msg = _('The lead can\'t be created')
        self._send_transient_message(partner, msg)
