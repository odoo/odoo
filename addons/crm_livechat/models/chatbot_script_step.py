# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, fields
from odoo.tools import html2plaintext


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    step_type = fields.Selection(
        selection_add=[("create_lead", "Create Lead")],
        ondelete={"create_lead": "cascade"},
    )
    crm_team_id = fields.Many2one(
        'crm.team', string='Sales Team', ondelete='set null', index="btree_not_null",
        help="Used in combination with 'create_lead' step type in order to automatically "
             "assign the created lead/opportunity to the defined team")

    def _chatbot_crm_prepare_lead_values(self, discuss_channel, description):
        name = self.env._("%s's New Lead", self.chatbot_script_id.title)
        if msg := self._find_first_user_free_input(discuss_channel):
            name = html2plaintext(msg.body)[:100]
        partner = self.env.user.partner_id
        team = self.crm_team_id
        if partner.company_id and team.company_id and partner.company_id != team.company_id:
            team = self.env["crm.team"]
        vals = {
            'description': description + discuss_channel._get_channel_history(),
            "name": name,
            "origin_channel_id": discuss_channel.id,
            'source_id': self.chatbot_script_id.source_id.id,
            "team_id": team.id,
            'user_id': False,
        }
        if team:
            vals["type"] = "lead" if team.use_leads else "opportunity"
        return vals


    def _process_step(self, discuss_channel):
        self.ensure_one()
        step_data = super()._process_step(discuss_channel)
        if self.step_type == 'create_lead':
            self._process_step_create_lead(discuss_channel)
        return step_data

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
            country = customer_values.get('country', False)
            create_values = {
                'email_from': customer_values['email'],
                'phone': customer_values['phone'],
                'lang_id': customer_values["lang"].id,
                'country_id': country.get('id', False) if country else False,
            }
        else:
            create_values = {"partner_id": self.env.user.partner_id.id}
        create_values.update(self._chatbot_crm_prepare_lead_values(
            discuss_channel, customer_values['description']))
        new_leads = self.env["crm.lead"].create(create_values)
        new_leads._assign_userless_lead_in_team(_('livechat discussion'))
        return new_leads
