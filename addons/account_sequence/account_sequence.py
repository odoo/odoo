# -*- coding: utf-8 -*-

from openerp import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    internal_sequence_number = fields.Char(string='Internal Number', readonly=True, copy=False, help='Internal Sequence Number')

    @api.multi
    def post(self):
        for move in self:
            if move.journal_id.internal_sequence_id:
                seq_no = move.journal_id.internal_sequence_id.next_by_id()
                move.internal_sequence_number = seq_no
        return super(AccountMove, self).post()


class AccountJournal(models.Model):
    _inherit = "account.journal"

    internal_sequence_id = fields.Many2one('ir.sequence', string='Internal Sequence', help="This sequence will be used to maintain the internal number for the journal entries related to this journal.")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    internal_sequence_number = fields.Char(related='move_id.internal_sequence_number', help='Internal Sequence Number', string='Internal Number', store=True)
