from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.multi
    def _reverse_move(self, date=None, journal_id=None, auto=False):
        self.ensure_one()
        reversed_move = self.copy(default={
            'date': date,
            'journal_id': journal_id.id if journal_id else self.journal_id.id,
            'ref': (_('Automatic reversal of: %s') if auto else _('Reversal of: %s')) % (self.name),
            'auto_reverse': False})
        for acm_line in reversed_move.line_ids.with_context(check_move_validity=False):
            acm_line.write({
                'debit': -acm_line.debit,
                'credit': -acm_line.credit,
                'amount_currency': -acm_line.amount_currency
            })
        self.reverse_entry_id = reversed_move
        return reversed_move

    @api.constrains("line_ids")
    def contol_lines(self):
        total_debit = 0
        total_credit = 0
        for line in self.line_ids:
            total_debit = total_debit + line.debit
            total_credit = total_credit + line.credit
        if total_debit != total_credit or total_debit == 0 or total_credit==0:
            raise ValidationError(_("L'écriture comptable n'est pas correcte"))




class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    _sql_constraints = [
        ('credit_debit2', 'CHECK (1=1)', 'Wrong credit or debit value in accounting entry !'),
    ]
