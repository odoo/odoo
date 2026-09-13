import textwrap

from odoo import api, fields, models
from odoo.fields import Domain


class ChatbotScriptAnswer(models.Model):
    _name = "chatbot.script.answer"
    _description = "Chatbot Script Answer"
    _order = "script_step_id, sequence, id"

    name = fields.Char(
        string="Answer",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=1)
    redirect_link = fields.Char(
        help="The visitor will be redirected to this link upon clicking the option "
        "(note that the script will end if the link is external to the livechat website)."
    )
    script_step_id = fields.Many2one(
        comodel_name="chatbot.script.step",
        index=True,
        required=True,
        ondelete="cascade",
    )
    chatbot_script_id = fields.Many2one(related="script_step_id.chatbot_script_id")

    @api.depends("script_step_id")
    @api.depends_context("chatbot_script_answer_display_short_name")
    def _compute_display_name(self):
        if self.env.context.get("chatbot_script_answer_display_short_name"):
            return super()._compute_display_name()

        for answer in self:
            if answer.script_step_id:
                answer_message = answer.script_step_id.message.replace("\n", " ")
                shortened_message = textwrap.shorten(
                    answer_message, width=26, placeholder=" [...]"
                )
                answer.display_name = f"{shortened_message}: {answer.name}"
            else:
                answer.display_name = answer.name

    @api.model
    def _search_display_name(self, operator, value):
        if value and operator == "ilike":
            return Domain("name", operator, value) | Domain(
                "script_step_id.message", operator, value
            )
        return super()._search_display_name(operator, value)

    def _to_store_defaults(self, target):
        return ["name", "redirect_link"]
