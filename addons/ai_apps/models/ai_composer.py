# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class AIComposer(models.Model):
    _name = "ai.composer"

    key = fields.Char("AI Key", help="The identifier of the mail assistant")
    default_prompt = fields.Text("Default Prompt", help="The default prompt passed to this mail assistant")
    system_prompt = fields.Text("System Prompt", help="The system prompt passed to this mail assistant - used for formatting")
