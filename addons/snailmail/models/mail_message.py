
from odoo import api, fields, models


class Message(models.Model):
    _inherit = 'mail.message'

    snailmail_error = fields.Boolean("Snailmail message in error", compute="_compute_snailmail_error", search="_search_snailmail_error")
    letter_ids = fields.One2many(comodel_name='snailmail.letter', inverse_name='message_id')
    message_type = fields.Selection(selection_add=[
        ('snailmail', 'Snailmail')
    ], ondelete={'snailmail': lambda recs: recs.write({'message_type': 'email'})})

    @api.depends('letter_ids', 'letter_ids.state')
    def _compute_snailmail_error(self):
        for message in self:
            if message.message_type == 'snailmail' and message.letter_ids:
                message.snailmail_error = message.letter_ids[0].state == 'error'
            else:
                message.snailmail_error = False

    def _search_snailmail_error(self, operator, operand):
        if operator == '=' and operand:
            return ['&', ('letter_ids.state', '=', 'error'), ('letter_ids.user_id', '=', self.env.user.id)]
        return ['!', '&', ('letter_ids.state', '=', 'error'), ('letter_ids.user_id', '=', self.env.user.id)]

    def cancel_letter(self):
        self.mapped('letter_ids').cancel()

    def send_letter(self):
        self.mapped('letter_ids')._snailmail_print()
