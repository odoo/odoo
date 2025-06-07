from odoo import api, fields, models

class SnailmailLetterFormatError(models.TransientModel):
    _name = 'snailmail.letter.format.error'
    _description = 'Format Error Sending a Snailmail Letter'

    message_id = fields.Many2one(
        'mail.message',
        default=lambda self: self.env.context.get('message_id', None),
    )
    snailmail_cover = fields.Boolean(
        string='Add a Cover Page',
        default=lambda self: self.env.company.snailmail_cover,
    )

    def update_resend_action(self):
        self.env.company.write({'snailmail_cover': self.snailmail_cover})
        letters_to_resend = self.message_id.letter_ids
        for letter in letters_to_resend:
            old_attachment = letter.attachment_id
            letter.attachment_id = False
            old_attachment.unlink()
            letter.write({'cover': self.snailmail_cover})
            letter.snailmail_print()

    def cancel_letter_action(self):
        self.message_id.cancel_letter()
