# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError


class WebsiteSearchableMixin(models.AbstractModel):
    _inherit = 'website.searchable.mixin'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_chatbot_redirect(self):
        if not (answers_sudo := self._get_chatbot_redirect_answers()):
            return
        # Don't block when user confirmed deletion, or from module uninstall
        # (the confirmation only counts if the dialog could show the answers to the user)
        confirmed = (
            self.env.context.get('website_url_dependencies_confirmed')
            and self.env['chatbot.script.answer'].has_access('read')
        )
        if confirmed or self.env.context.get('force_delete'):
            answers_sudo.redirect_record_ref = False
        else:
            raise UserError(self.env._(
                "You cannot delete a record used as redirection by the following chatbot answers:\n%(answers)s",
                answers=self._format_chatbot_redirect_answers(answers_sudo),
            ))

    def write(self, vals):
        if 'active' in vals and not vals['active'] and (answers_sudo := self._get_chatbot_redirect_answers()):
            raise UserError(self.env._(
                "You cannot archive a record used as redirection by the following chatbot answers:\n%(answers)s",
                answers=self._format_chatbot_redirect_answers(answers_sudo),
            ))
        if 'is_published' in vals and not vals['is_published'] and (answers_sudo := self._get_chatbot_redirect_answers()):
            raise UserError(self.env._(
                "You cannot unpublish a record used as redirection by the following chatbot answers:\n%(answers)s",
                answers=self._format_chatbot_redirect_answers(answers_sudo),
            ))
        return super().write(vals)

    def _get_chatbot_redirect_answers(self):
        # sudo - chatbot.script.answer: any user deleting, archiving or unpublishing a record must
        # know it is used by a chatbot
        return self.env['chatbot.script.answer'].sudo().search([
            ('redirect_record_ref', 'in', [f'{record._name},{record.id}' for record in self]),
        ])

    def _format_chatbot_redirect_answers(self, answers):
        return "\n".join(f"- {answer.chatbot_script_id.title}: {answer.display_name}" for answer in answers)
