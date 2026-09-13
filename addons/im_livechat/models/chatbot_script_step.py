from collections import defaultdict

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.tools import email_normalize, html2plaintext

from odoo.addons.mail.tools.discuss import Store


class ChatbotScriptStep(models.Model):
    _name = "chatbot.script.step"
    _description = "Chatbot Script Step"
    _order = "sequence, id"

    name = fields.Char(compute="_compute_name")
    message = fields.Html(translate=True)
    sequence = fields.Integer()
    chatbot_script_id = fields.Many2one(
        comodel_name="chatbot.script",
        string="Chatbot",
        index=True,
        required=True,
        ondelete="cascade",
    )
    step_type = fields.Selection(
        selection=[
            ("text", "Text"),
            ("question_selection", "Question"),
            ("question_email", "Email"),
            ("question_phone", "Phone"),
            ("forward_operator", "Forward to Operator"),
            ("free_input_single", "Free Input"),
            ("free_input_multi", "Free Input (Multi-Line)"),
        ],
        default="text",
        required=True,
    )
    answer_ids = fields.One2many(
        comodel_name="chatbot.script.answer",
        inverse_name="script_step_id",
        string="Answers",
        copy=True,
    )
    triggering_answer_ids = fields.Many2many(
        comodel_name="chatbot.script.answer",
        string="Only If",
        compute="_compute_triggering_answer_ids",
        store=True,
        copy=False,
        readonly=False,
        domain="[('script_step_id.sequence', '<', sequence), ('script_step_id.chatbot_script_id', '=', chatbot_script_id)]",
        help="Show this step only if all of these answers have been selected.",
    )
    is_forward_operator = fields.Boolean(compute="_compute_is_forward_operator")
    is_forward_operator_child = fields.Boolean(
        compute="_compute_is_forward_operator_child"
    )
    operator_expertise_ids = fields.Many2many(
        comodel_name="im_livechat.expertise",
        help="When forwarding live chat conversations, the chatbot will prioritize users with matching expertise.",
    )

    @api.depends("sequence", "chatbot_script_id")
    @api.depends_context("lang")
    def _compute_name(self):
        for step in self:
            step.name = self.env._(
                "%(title)s - Step %(sequence)d",
                title=step.chatbot_script_id.title,
                sequence=step.sequence,
            )

    @api.depends("sequence")
    def _compute_triggering_answer_ids(self):
        for step in self.filtered("triggering_answer_ids"):
            update_command = [
                Command.unlink(answer.id)
                for answer in step.triggering_answer_ids
                if answer.script_step_id.sequence >= step.sequence
            ]
            if update_command:
                step.triggering_answer_ids = update_command

    @api.depends("step_type")
    def _compute_is_forward_operator(self):
        for step in self:
            step.is_forward_operator = step.step_type == "forward_operator"

    @api.depends(
        "chatbot_script_id.script_step_ids.answer_ids",
        "chatbot_script_id.script_step_ids.is_forward_operator",
        "chatbot_script_id.script_step_ids.sequence",
        "chatbot_script_id.script_step_ids.step_type",
        "chatbot_script_id.script_step_ids.triggering_answer_ids",
        "sequence",
        "triggering_answer_ids",
    )
    def _compute_is_forward_operator_child(self):
        parent_steps_by_chatbot = {}
        for chatbot in self.chatbot_script_id:
            parent_steps_by_chatbot[chatbot.id] = chatbot.script_step_ids.filtered(
                lambda step: (
                    step.is_forward_operator or step.step_type == "question_selection"
                )
            ).sorted(lambda s: s.sequence, reverse=True)
        for step in self:
            parent_steps = parent_steps_by_chatbot[step.chatbot_script_id.id].filtered(
                lambda s: s.sequence < step.sequence
            )
            parent = step
            while True:
                parent = parent._get_parent_step(parent_steps)
                if not parent or parent.is_forward_operator:
                    break
            step.is_forward_operator_child = parent and parent.is_forward_operator

    @api.model_create_multi
    def create(self, vals_list):
        vals_by_chatbot_id = {}
        for vals in vals_list:
            chatbot_id = vals.get("chatbot_script_id")
            if chatbot_id:
                step_values = vals_by_chatbot_id.get(chatbot_id, [])
                step_values.append(vals)
                vals_by_chatbot_id[chatbot_id] = step_values

        read_group_results = self.env["chatbot.script.step"]._read_group(
            [("chatbot_script_id", "in", list(vals_by_chatbot_id))],
            ["chatbot_script_id"],
            ["sequence:max"],
        )
        max_sequence_by_chatbot = {
            chatbot_script.id: sequence
            for chatbot_script, sequence in read_group_results
        }

        for chatbot_id, step_vals in vals_by_chatbot_id.items():
            current_sequence = 0
            if chatbot_id in max_sequence_by_chatbot:
                current_sequence = max_sequence_by_chatbot[chatbot_id] + 1

            for vals in step_vals:
                if "sequence" in vals:
                    current_sequence = vals.get("sequence")
                else:
                    vals["sequence"] = current_sequence
                    current_sequence += 1

        return super().create(vals_list)

    def _chatbot_prepare_customer_values(
        self, discuss_channel, create_partner=True, update_partner=True
    ):
        partner = False
        user_inputs = discuss_channel._chatbot_find_customer_values_in_messages(
            {
                "question_email": "email",
                "question_phone": "phone",
            }
        )
        input_email = user_inputs.get("email", False)
        input_phone = user_inputs.get("phone", False)

        if self.env.user._is_public() and create_partner:
            partner = self.env["res.partner"].create(
                {
                    "name": input_email,
                    "email": input_email,
                    "phone_ids": [Command.create({"number": input_phone})]
                    if input_phone
                    else [],
                }
            )
        elif not self.env.user._is_public():
            partner = self.env.user.partner_id
            if update_partner:
                update_values = {}
                if input_email and not partner.email:
                    update_values["email"] = input_email
                if input_phone and not partner.phone_ids:
                    update_values["phone_ids"] = [
                        Command.create({"number": input_phone})
                    ]
                if update_values:
                    partner.write(update_values)

        description = Markup("")
        if input_email:
            description += Markup("%s<strong>%s</strong><br>") % (
                _("Email: "),
                input_email,
            )
        if input_phone:
            description += Markup("%s<strong>%s</strong><br>") % (
                _("Phone: "),
                input_phone,
            )
        if description:
            description += Markup("<br>")

        return {
            "partner": partner,
            "email": input_email,
            "phone": input_phone,
            "description": description,
        }

    def _find_first_user_free_input(self, discuss_channel):
        chatbot_partner = self.chatbot_script_id.operator_partner_id
        user_answers = discuss_channel.chatbot_message_ids.filtered(
            lambda m: m.mail_message_id.author_id != chatbot_partner
        ).sorted("id")
        for answer in user_answers:
            if answer.script_step_id.step_type in (
                "free_input_single",
                "free_input_multi",
            ):
                return answer.mail_message_id
        return self.env["mail.message"]

    def _get_next_step(self, selected_answer_ids):
        self.check_singleton()
        domain = Domain("chatbot_script_id", "=", self.chatbot_script_id.id) & Domain(
            "sequence", ">", self.sequence
        )
        if selected_answer_ids:
            domain &= Domain(
                "triggering_answer_ids", "in", selected_answer_ids.ids + [False]
            )
        steps = self.env["chatbot.script.step"].search(domain)
        for step in steps:
            if not step.triggering_answer_ids:
                return step
            answers_by_step = defaultdict(list)
            for answer in step.triggering_answer_ids:
                answers_by_step[answer.script_step_id.id].append(answer)
            if all(
                any(answer in step_triggering_answers for answer in selected_answer_ids)
                for step_triggering_answers in answers_by_step.values()
            ):
                return step
        return self.env["chatbot.script.step"]

    def _get_parent_step(self, all_parent_steps):
        self.check_singleton()

        if not self.chatbot_script_id.ids:
            return self.env["chatbot.script.step"]

        for step in all_parent_steps:
            if step.sequence >= self.sequence:
                continue
            if self.triggering_answer_ids:
                if not (
                    all(
                        answer in self.triggering_answer_ids
                        for answer in step.triggering_answer_ids
                    )
                    or any(
                        answer in self.triggering_answer_ids
                        for answer in step.answer_ids
                    )
                ):
                    continue
            elif step.triggering_answer_ids:
                continue
            return step
        return self.env["chatbot.script.step"]

    def _is_last_step(self, discuss_channel=False):
        self.check_singleton()
        discuss_channel = discuss_channel or self.env["discuss.channel"]

        if self.step_type != "question_selection" and not self._get_next_step(
            discuss_channel.sudo().chatbot_message_ids.user_script_answer_id
        ):
            return True

        return False

    def _process_answer(self, discuss_channel, message_body):
        self.check_singleton()

        user_text_answer = html2plaintext(message_body)
        if self.step_type == "question_email" and not email_normalize(user_text_answer):
            raise ValidationError(_('"%s" is not a valid email.', user_text_answer))

        if self.step_type in [
            "question_email",
            "question_phone",
            "free_input_single",
            "free_input_multi",
        ]:
            chatbot_message = self.env["chatbot.message"].search(
                [
                    ("discuss_channel_id", "=", discuss_channel.id),
                    ("script_step_id", "=", self.id),
                ],
                limit=1,
            )

            if chatbot_message:
                chatbot_message.write({"user_raw_answer": message_body})
                self.env.flush_all()

        return self._get_next_step(
            discuss_channel.sudo().chatbot_message_ids.user_script_answer_id
        )

    def _process_step(self, discuss_channel):
        self.check_singleton()
        if self.step_type == "forward_operator":
            return discuss_channel._forward_human_operator(chatbot_script_step=self)
        return discuss_channel._chatbot_post_message(
            self.chatbot_script_id, self.message
        )

    def _to_store_defaults(self, target):
        return [
            Store.Many("answer_ids"),
            Store.Attr("is_last", lambda step: step._is_last_step()),
            "message",
            "step_type",
        ]
