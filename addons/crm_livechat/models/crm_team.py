# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError
from odoo.tools.i18n import format_list


class CrmTeam(models.Model):
    _inherit = "crm.team"

    def write(self, values):
        if not values.get("active", True):
            self._ensure_no_forward_chatbot_step()
        return super().write(values)

    def unlink(self):
        self._ensure_no_forward_chatbot_step()
        return super().unlink()

    def _ensure_no_forward_chatbot_step(self):
        domain = [("crm_team_id", "in", self.ids), ("step_type", "=", "create_lead_and_forward")]
        # sudo: chatbot.script.step - leaking chatbot name related to specific sales team is acceptable
        if steps := self.env["chatbot.script.step"].sudo().search(domain):
            raise UserError(
                self.env._(
                    "These sales team cannot be archived or deleted because they are connected to the following chatbots: %(chatbots)s.\n"
                    "To proceed, update the “Create Lead & Forward” steps of these chatbots to use a different sales team.",
                    chatbots=format_list(self.env, steps.chatbot_script_id.mapped("title")),
                )
            )
