
from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    snailmail_error = fields.Boolean(
        string="Snailmail message in error",
        compute="_compute_snailmail_error", search="_search_snailmail_error")
    letter_ids = fields.One2many(comodel_name='snailmail.letter', inverse_name='message_id')
    message_type = fields.Selection(
        selection_add=[('snailmail', 'Snailmail')],
        ondelete={'snailmail': lambda recs: recs.write({'message_type': ' comment'})})

    @api.depends('letter_ids', 'letter_ids.state')
    def _compute_snailmail_error(self):
        self.snailmail_error = False
        for message in self.filtered(lambda msg: msg.message_type == 'snailmail' and msg.letter_ids):
            message.snailmail_error = message.letter_ids[0].state == 'error'

    def _search_snailmail_error(self, operator, operand):
        if operator != 'in':
            return NotImplemented
        return ['&', ('letter_ids.state', '=', 'error'), ('letter_ids.user_id', '=', self.env.user.id)]

    def cancel_letter(self):
        self.letter_ids.cancel()

    def send_letter(self):
        self.letter_ids._snailmail_print()
