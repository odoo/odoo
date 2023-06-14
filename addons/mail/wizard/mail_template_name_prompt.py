from odoo import models, fields


class MailTemplateNamePrompt(models.TransientModel):
    _name = 'mail.template.name.prompt'
    _description = 'Prompt for inputting name when saving a template'

    name = fields.Char('Name')

    def save_template(self):
        return self.env['mail.compose.message'].browse(
            [self._context['mail_compose_message_id']],
        )._save_as_template(self.name)

    def cancel(self):
        return self._context['reopen_composer']
