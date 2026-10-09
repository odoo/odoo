# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class WebsiteSearchableMixin(models.AbstractModel):
    _inherit = 'website.searchable.mixin'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_chatbot_redirect(self):
        # sudo - chatbot.script.answer: any user deleting a record must know it is used by a chatbot
        answers_sudo = self.env['chatbot.script.answer'].sudo().search([
            ('redirect_record_ref', 'in', [f'{record._name},{record.id}' for record in self]),
        ])
        if answers_sudo:
            raise UserError(_(
                "You cannot delete a record used as redirection by the following chatbot answers:\n%(answers)s",
                answers="\n".join(
                    f"- {answer.chatbot_script_id.title}: {answer.display_name}" for answer in answers_sudo
                ),
            ))
