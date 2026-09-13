from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import (
    email_normalize,
    get_lang,
    html2plaintext,
    is_html_empty,
    plaintext2html,
)

from odoo.addons.mail.tools.discuss import Store


class ChatbotScript(models.Model):
    _name = "chatbot.script"
    _description = "Chatbot Script"
    _inherit = ["mixin.image", "mixin.utm.source"]
    _rec_name = "title"
    _order = "title, id"

    title = fields.Char(
        translate=True,
        default="Chatbot",
        required=True,
    )
    active = fields.Boolean(default=True)
    image_1920 = fields.Image(
        related="operator_partner_id.image_1920",
        readonly=False,
    )

    script_step_ids = fields.One2many(
        comodel_name="chatbot.script.step",
        inverse_name="chatbot_script_id",
        string="Script Steps",
        copy=True,
    )
    operator_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Bot Operator",
        index=True,
        copy=False,
        required=True,
        ondelete="restrict",
    )
    livechat_channel_count = fields.Integer(compute="_compute_livechat_channel_count")
    first_step_warning = fields.Selection(
        selection=[
            ("first_step_operator", "First Step Operator"),
            ("first_step_invalid", "First Step Invalid"),
        ],
        compute="_compute_first_step_warning",
    )

    @api.constrains("script_step_ids")
    def _check_question_selection(self):
        for step in self.script_step_ids:
            if step.step_type == "question_selection" and not step.answer_ids:
                raise ValidationError(
                    self.env._("Step of type 'Question' must have answers.")
                )

    @api.onchange("script_step_ids")
    def _onchange_script_step_ids(self):
        for step in self.script_step_ids:
            if step.step_type != "question_selection" and step.answer_ids:
                step.answer_ids = [Command.clear()]

    def _compute_livechat_channel_count(self):
        channels_data = self.env["im_livechat.channel.rule"]._read_group(
            [("chatbot_script_id", "in", self.ids)],
            ["chatbot_script_id"],
            ["channel_id:count_distinct"],
        )
        mapped_channels = {
            chatbot_script.id: count_distinct
            for chatbot_script, count_distinct in channels_data
        }
        for script in self:
            script.livechat_channel_count = mapped_channels.get(script.id, 0)

    @api.depends("script_step_ids.is_forward_operator", "script_step_ids.step_type")
    def _compute_first_step_warning(self):
        for script in self:
            allowed_first_step_types = [
                "question_selection",
                "question_email",
                "question_phone",
                "free_input_single",
                "free_input_multi",
            ]
            welcome_steps = script.script_step_ids and script._get_welcome_steps()
            if welcome_steps and welcome_steps[-1].is_forward_operator:
                script.first_step_warning = "first_step_operator"
            elif (
                welcome_steps
                and welcome_steps[-1].step_type not in allowed_first_step_types
            ):
                script.first_step_warning = "first_step_invalid"
            else:
                script.first_step_warning = False

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, title=self.env._("%s (copy)", script.title))
            for script, vals in zip(self, vals_list)
        ]

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "title"))
        self._copy_translations_of_renamed_field(
            new, "title", lambda record, term: record.env._("%s (copy)", term)
        )

    def copy(self, default=None):
        default = default or {}
        new_scripts = super().copy(default=default)
        if "question_ids" in default:
            return new_scripts

        for old_script, new_script in zip(self, new_scripts):
            original_steps = old_script.script_step_ids.sorted()
            clone_steps = new_script.script_step_ids.sorted()

            answers_map = {}
            for clone_step, original_step in zip(clone_steps, original_steps):
                for clone_answer, original_answer in zip(
                    clone_step.answer_ids.sorted(), original_step.answer_ids.sorted()
                ):
                    answers_map[original_answer] = clone_answer

            for clone_step, original_step in zip(clone_steps, original_steps):
                clone_step.write(
                    {
                        "triggering_answer_ids": [
                            (4, answer.id)
                            for answer in [
                                answers_map[original_answer]
                                for original_answer in original_step.triggering_answer_ids
                            ]
                        ]
                    }
                )
        return new_scripts

    @api.model_create_multi
    def create(self, vals_list):
        operator_partners_values = [
            {
                "name": vals["title"],
                "image_1920": vals.get("image_1920", False),
                "active": False,
            }
            for vals in vals_list
            if "operator_partner_id" not in vals and "title" in vals
        ]

        operator_partners = self.env["res.partner"].create(operator_partners_values)

        for vals, partner in zip(
            [
                vals
                for vals in vals_list
                if "operator_partner_id" not in vals and "title" in vals
            ],
            operator_partners,
        ):
            vals["operator_partner_id"] = partner.id

        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)

        if "title" in vals:
            self.operator_partner_id.write({"name": vals["title"]})

        return res

    def _get_welcome_steps(self):
        self.check_singleton()

        welcome_steps = self.env["chatbot.script.step"]
        for step in self.script_step_ids:
            welcome_steps += step
            if step.step_type != "text":
                break

        return welcome_steps

    def _post_welcome_steps(self, discuss_channel):
        self.check_singleton()
        posted_messages = self.env["mail.message"]

        for welcome_step in self._get_welcome_steps():
            discuss_channel.chatbot_current_step_id = welcome_step.id

            if not is_html_empty(welcome_step.message):
                posted_messages += discuss_channel.with_context(
                    mail_post_autofollow_author_skip=True
                ).message_post(
                    author_id=self.operator_partner_id.id,
                    body=plaintext2html(welcome_step.message, with_paragraph=False),
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )

        return posted_messages

    def action_view_livechat_channels(self):
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "im_livechat.im_livechat_channel_action"
        )
        action["domain"] = [("rule_ids.chatbot_script_id", "in", self.ids)]
        return action

    def _to_store_defaults(self, target):
        return [Store.One("operator_partner_id", ["name"]), "title"]

    def _get_email_check(self, email_address, discuss_channel):
        email_address = html2plaintext(email_address)
        email_normalized = email_normalize(email_address)

        posted_message = False
        error_message = False
        if not email_normalized:
            error_message = self.env._(
                "'%(input_email)s' does not look like a valid email. Can you please try again?",
                input_email=email_address,
            )
            posted_message = discuss_channel._chatbot_post_message(
                self, plaintext2html(error_message)
            )

        return {
            "success": bool(email_normalized),
            "posted_message": posted_message,
            "error_message": error_message,
        }

    def _get_chatbot_language(self):
        return get_lang(
            self.env,
            lang_code=request and request.httprequest.cookies.get("frontend_lang"),
        ).code
