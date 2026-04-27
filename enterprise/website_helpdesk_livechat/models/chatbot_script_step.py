# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, fields


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    step_type = fields.Selection(
        selection_add=[('create_ticket', 'Create Ticket')], ondelete={'create_ticket': 'cascade'})
    helpdesk_team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', ondelete='set null')

    def _prepare_ticket_values(self, discuss_channel, description):
        name = _("%(name)s's Ticket",
            name=discuss_channel.livechat_visitor_id.display_name or self.chatbot_script_id.title)

        return {
            'description': description + discuss_channel._get_channel_history(),
            'name': name,
            'source_id': self.chatbot_script_id.source_id.id,
            'team_id': self.helpdesk_team_id.id,
        }

    def _process_step(self, discuss_channel):
        self.ensure_one()

        posted_message = super()._process_step(discuss_channel)

        if self.step_type == 'create_ticket':
            self._process_step_create_ticket(discuss_channel)

        return posted_message

    def _process_step_create_ticket(self, discuss_channel):
        """ When reaching a 'create_ticket' step, we extract the relevant information: visitor's
        email, phone and conversation history to create a helpdesk.ticket.

        We use the email and phone to update the environment partner's information (if not a public
        user) if they differ from the current values.

        The whole conversation history will be saved into the ticket's description for reference.
        This also allows having a question of type 'free_input_multi' to let the visitor explain
        his issue before creating the ticket. """

        customer_values = self._chatbot_prepare_customer_values(
            discuss_channel, create_partner=True, update_partner=True)

        self.env['helpdesk.ticket'].create({
            'partner_id': customer_values['partner'].id,
            **self._prepare_ticket_values(discuss_channel, customer_values['description']),
        })
