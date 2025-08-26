# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import _, models, fields
from odoo.fields import Domain
from odoo.tools import html2plaintext


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    step_type = fields.Selection(
        selection_add=[
            ("create_lead", "Create Lead"),
            ("create_lead_and_forward", "Create Lead & Forward"),
        ],
        ondelete={"create_lead": "cascade", "create_lead_and_forward": "cascade"},
    )
    crm_team_id = fields.Many2one(
        'crm.team', string='Sales Team', ondelete='set null', index="btree_not_null",
        help="Used in combination with 'create_lead' step type in order to automatically "
             "assign the created lead/opportunity to the defined team")

    def _compute_is_forward_operator(self):
        super()._compute_is_forward_operator()
        self.filtered(lambda s: s.step_type == "create_lead_and_forward").is_forward_operator = True

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
        if self.step_type == "create_lead_and_forward":
            return self._process_step_create_lead_and_forward(discuss_channel)
        posted_message = super()._process_step(discuss_channel)
        if self.step_type == 'create_lead':
            self._process_step_create_lead(discuss_channel)
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
            create_values = {"partner_id": self.env.user.partner_id.id}
        create_values.update(self._chatbot_crm_prepare_lead_values(
            discuss_channel, customer_values['description']))
        new_leads = self.env["crm.lead"].create(create_values)
        new_leads._assign_userless_lead_in_team(_('livechat discussion'))
        return new_leads

    def _process_step_create_lead_and_forward(self, discuss_channel):
        lead = self._process_step_create_lead(discuss_channel)
        teams = lead.team_id
        if not teams:
            possible_teams = self.env["crm.team"].search(
                Domain("assignment_optout", "=", False) & (
                    Domain("use_leads", "=", True) | Domain("use_opportunities", "=", True)
                ),
            )
            teams = possible_teams.filtered(
                lambda team: team.assignment_max
                and lead.filtered_domain(literal_eval(team.assignment_domain or "[]"))
            )
        if self.env.user.partner_id.company_id:
            teams = teams.filtered(
                lambda team: not team.company_id
                or team.company_id == self.env.user.partner_id.company_id
            )
        assignable_user_ids = [
            member.user_id.id
            for member in teams.crm_team_member_ids
            if not member.assignment_optout
            and member._get_assignment_quota() > 0
            and lead.filtered_domain(literal_eval(member.assignment_domain or "[]"))
        ]
        previous_operator = discuss_channel.livechat_operator_id
        users = self.env["res.users"]
        if discuss_channel.livechat_channel_id:
            # sudo: im_livechat.channel - getting available operators is acceptable
            users = discuss_channel.livechat_channel_id.sudo()._get_available_operators_by_livechat_channel(
                self.env["res.users"].browse(assignable_user_ids)
            )[discuss_channel.livechat_channel_id]
        message = discuss_channel._forward_human_operator(self, users=users)
        if previous_operator != discuss_channel.livechat_operator_id:
            user = next(user for user in users if user.partner_id == discuss_channel.livechat_operator_id)
            lead.user_id = user
            lead.team_id = next(team for team in teams if user in team.crm_team_member_ids.user_id)
            msg = self.env._("Created a new lead: %s", lead._get_html_link())
            user._bus_send_transient_message(discuss_channel, msg)
            # Call flush_recordset() now (as sudo), otherwise flush_all() is called at the end of
            # the request with a non-sudo env, which fails (as public user) to compute some crm.lead
            # fields having dependencies on assigned user_id.
            lead.flush_recordset()
        return message
