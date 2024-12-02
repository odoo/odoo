# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import _, models, fields
from odoo.tools import plaintext2html


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    step_type = fields.Selection(
        selection_add=[
            ("create_lead", "Create Lead"),
            ("create_lead_and_forward", "Create Lead & Forward")
        ], ondelete={"create_lead": "cascade", "create_lead_and_forward": "cascade"})
    crm_team_id = fields.Many2one(
        'crm.team', string='Sales Team', ondelete='set null',
        help="Used in combination with 'create_lead' step type in order to automatically "
             "assign the created lead/opportunity to the defined team")

    def _chatbot_crm_prepare_lead_values(self, discuss_channel, description):
        return {
            'description': description + discuss_channel._get_channel_history(),
            'name': _("%s's New Lead", self.chatbot_script_id.title),
            'source_id': self.chatbot_script_id.source_id.id,
            'team_id': self.crm_team_id.id,
            'type': 'lead' if self.crm_team_id.use_leads else 'opportunity',
            'user_id': False,
        }

    def _process_step(self, discuss_channel):
        self.ensure_one()

        posted_message = super()._process_step(discuss_channel)

        if self.step_type == 'create_lead':
            self._process_step_create_lead(discuss_channel)
        elif self.step_type == "create_lead_and_forward":
            return self._process_step_create_lead_and_forward(discuss_channel, posted_message)

        return posted_message

    def _process_step_create_lead(self, discuss_channel):
        """ When reaching a 'create_lead' step, we extract the relevant information: visitor's
        email, phone and conversation history to create a crm.lead.

        We use the email and phone to update the environment partner's information (if not a public
        user) if they differ from the current values.

        The whole conversation history will be saved into the lead's description for reference.
        This also allows having a question of type 'free_input_multi' to let the visitor explain
        their interest / needs before creating the lead. """

        customer_values = self._chatbot_prepare_customer_values(
            discuss_channel, create_partner=False, update_partner=True)
        if self.env.user._is_public():
            create_values = {
                'email_from': customer_values['email'],
                'phone': customer_values['phone'],
            }
        else:
            partner = self.env.user.partner_id
            create_values = {
                'partner_id': partner.id,
                'company_id': partner.company_id.id,
            }

        create_values.update(self._chatbot_crm_prepare_lead_values(
            discuss_channel, customer_values['description']))

        return self.env['crm.lead'].create(create_values)

    def _process_step_create_lead_and_forward(self, discuss_channel, posted_message):
        lead = self._process_step_create_lead(discuss_channel)
        team = self.crm_team_id
        domain = literal_eval(team.assignment_domain or "[]")
        lead = lead.filtered_domain(domain)
        if team and lead:
            member_to_assign = next(
                (
                    member for member in team.crm_team_member_ids
                    if not member.assignment_optout
                    and member._get_assignment_quota() > 0
                ),
                None
            )
            if member_to_assign:
                lead.user_id = member_to_assign.user_id
                if member_to_assign.user_id._is_user_available():
                    user = member_to_assign.user_id
                    discuss_channel.with_user(user).sudo().add_members(user.partner_id.ids, open_chat_window=True)
                    # sudo - discuss.channel: let the chat bot proceed to the forward step (change channel operator, add human operator
                    # as member, remove bot from channel, rename channel and finally broadcast the channel to the new operator).
                    channel_sudo = discuss_channel.sudo()
                    channel_sudo.livechat_operator_id = user.partner_id
                    if bot_member := channel_sudo.channel_member_ids.filtered(
                        lambda m: m.partner_id == self.chatbot_script_id.operator_partner_id
                    ):
                        channel_sudo._action_unfollow(partner=bot_member.partner_id)
                    channel_sudo.name = user.livechat_username or user.name
                    channel_sudo._broadcast(user.partner_id.ids)
                    return posted_message
        return self._process_step_forward_operator(discuss_channel, posted_message)

    def _get_operator_step_types(self):
        return super()._get_operator_step_types() + ["create_lead_and_forward"]
