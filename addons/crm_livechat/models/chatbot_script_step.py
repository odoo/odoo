# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


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

    _create_lead_and_forward_has_sales_team = models.Constraint(
        "CHECK(step_type != 'create_lead_and_forward' or crm_team_id IS NOT NULL)",
        "Create Lead & Forward steps must have a sales team defined.",
    )

    def _compute_is_forward_operator(self):
        super()._compute_is_forward_operator()
        self.filtered(lambda s: s.step_type == "create_lead_and_forward").is_forward_operator = True

    def _chatbot_crm_prepare_lead_values(self, discuss_channel, description):
        return {
            "company_id": self.crm_team_id.company_id.id,
            'description': description + discuss_channel._get_channel_history(),
            "name": self.env._("%s's New Lead", self.chatbot_script_id.title),
            'source_id': self.chatbot_script_id.source_id.id,
            'team_id': self.crm_team_id.id,
            'type': 'lead' if self.crm_team_id.use_leads else 'opportunity',
            'user_id': False,
        }

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
            partner = self.env.user.partner_id
            create_values = {
                'partner_id': partner.id,
                'company_id': partner.company_id.id,
            }
        create_values.update(self._chatbot_crm_prepare_lead_values(
            discuss_channel, customer_values['description']))
        return self.env["crm.lead"].create(create_values)

    def _process_step_create_lead_and_forward(self, discuss_channel):
        lead = self._process_step_create_lead(discuss_channel)
        assignable_user_ids = [
            member.user_id.id
            for member in lead.team_id.crm_team_member_ids
            if not member.assignment_optout and member._get_assignment_quota() > 0
        ]
        # sudo: im_livechat.channel - getting available operators is acceptable
        users = discuss_channel.livechat_channel_id.sudo()._get_available_operators_by_livechat_channel(
            self.env["res.users"].browse(assignable_user_ids)
        )[discuss_channel.livechat_channel_id]
        message = self._process_step_forward_operator(discuss_channel, users=users)
        operator_partner = discuss_channel.livechat_operator_id
        if operator_partner != self.chatbot_script_id.operator_partner_id:
            lead.user_id = next(user for user in users if user.partner_id == operator_partner)
            # Call flush_recordset() now (as sudo), otherwise flush_all() is called at the end of
            # the request with a non-sudo env, which fails (as public user) to compute some crm.lead
            # fields having dependencies on assigned user_id.
            lead.flush_recordset()
        return message
