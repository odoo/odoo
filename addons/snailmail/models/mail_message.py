
from odoo import api, fields, models

class Message(models.Model):
    _inherit = 'mail.message'

    snailmail_error = fields.Boolean("Snailmail message in error", compute="_compute_snailmail_error", search="_search_snailmail_error")
    snailmail_status = fields.Char("Snailmail Status", compute="_compute_snailmail_error")
    letter_ids = fields.One2many(comodel_name='snailmail.letter', inverse_name='message_id')
    message_type = fields.Selection(selection_add=[('snailmail', 'Snailmail')])

    def _get_message_format_fields(self):
        res = super(Message, self)._get_message_format_fields()
        res.append('snailmail_error')
        res.append('snailmail_status')
        return res

    @api.depends('letter_ids', 'letter_ids.state')
    def _compute_snailmail_error(self):
        for message in self:
            if message.message_type == 'snailmail' and message.letter_ids:
                message.snailmail_error = message.letter_ids[0].state == 'error'
                message.snailmail_status = message.letter_ids[0].error_code if message.letter_ids[0].state == 'error' else message.letter_ids[0].state
            else:
                message.snailmail_error = False
                message.snailmail_status = ''

    def _search_snailmail_error(self, operator, operand):
        if operator == '=' and operand:
            return ['&', ('letter_ids.state', '=', 'error'), ('letter_ids.user_id', '=', self.env.user.id)]
        return ['!', '&', ('letter_ids.state', '=', 'error'), ('letter_ids.user_id', '=', self.env.user.id)] 

    def cancel_letter(self):
        self.mapped('letter_ids').cancel()

    def send_letter(self):
        self.mapped('letter_ids')._snailmail_print()

    def message_fetch_failed(self):
        res = super(Message, self).message_fetch_failed()
        failed_letters = self.letter_ids.fetch_failed_letters()
        return res + failed_letters
