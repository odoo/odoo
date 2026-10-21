# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class WebsiteSearchableMixin(models.AbstractModel):
    _inherit = 'website.searchable.mixin'

    def _get_chatbot_redirect_answers(self):
        # sudo - chatbot.script.answer: any user deleting, archiving or unpublishing a record must
        # know it is used by a chatbot
        return self.env['chatbot.script.answer'].sudo().search([
            ('redirect_record_ref', 'in', [f'{record._name},{record.id}' for record in self]),
        ])

    def _format_chatbot_redirect_answers(self, answers):
        return "\n".join(f"- {answer.chatbot_script_id.title}: {answer.display_name}" for answer in answers)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_chatbot_redirect(self):
        if not (answers_sudo := self._get_chatbot_redirect_answers()):
            return
        # deletion confirmed from the dialog listing the answers, see `search_url_dependencies`
        if self.env.context.get('website_url_dependencies_confirmed'):
            answers_sudo.redirect_record_ref = False
        else:
            raise UserError(_(
                "You cannot delete a record used as redirection by the following chatbot answers:\n%(answers)s",
                answers=self._format_chatbot_redirect_answers(answers_sudo),
            ))

    def write(self, vals):
        if 'active' in vals and not vals['active'] and (answers_sudo := self._get_chatbot_redirect_answers()):
            raise UserError(_(
                "You cannot archive a record used as redirection by the following chatbot answers:\n%(answers)s",
                answers=self._format_chatbot_redirect_answers(answers_sudo),
            ))
        if 'is_published' in vals and not vals['is_published'] and (answers_sudo := self._get_chatbot_redirect_answers()):
            raise UserError(_(
                "You cannot unpublish a record used as redirection by the following chatbot answers:\n%(answers)s",
                answers=self._format_chatbot_redirect_answers(answers_sudo),
            ))
        return super().write(vals)
