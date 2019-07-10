
from odoo import api, fields, models

class SnailmailLetterFormatError(models.TransientModel):
    _name = 'snailmail.letter.format.error'
    _description = 'Format Error Sending a Snailmail Letter'

    message_id = fields.Many2one('mail.message')
    snailmail_cover = fields.Boolean(string='Add a Cover Page')

    @api.model
    def default_get(self, fields):
        res = super(SnailmailLetterFormatError, self).default_get(fields)
        snailmail_cover = self.env.company.snailmail_cover
        res.update({
            'message_id': self.env.context.get('message_id'),
            'snailmail_cover': snailmail_cover,
        })
        return res

    def update_resend_action(self):
        self.env.company.write({'snailmail_cover': self.snailmail_cover})
        letters_to_resend = self.env['snailmail.letter'].search([
            ('error_code', '=', 'FORMAT_ERROR'),
        ])
        for letter in letters_to_resend:
            letter.attachment_id.unlink()
            letter.write({'cover': self.snailmail_cover})
            letter.snailmail_print()

    def cancel_letter_action(self):
        self.message_id.cancel_letter()
