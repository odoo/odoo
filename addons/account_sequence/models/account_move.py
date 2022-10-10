# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    name = fields.Char(compute='_compute_name')
    highest_name = fields.Char(compute='_compute_highest_name')

    def _get_journal_sequence(self):
        if self.move_type in ('out_refund', 'in_refund') and self.journal_id.type in ('sale', 'purchase') \
                and self.journal_id.refund_sequence_id:
            return self.journal_id.refund_sequence_id._get_current_sequence()
        else:
            return self.journal_id.sequence_id._get_current_sequence()

    @api.depends('state', 'journal_id', 'date')
    def _compute_name(self):
        # OVERRIDE
        moves_with_ir_sequence = self.filtered('journal_id.sequence_id')
        for move in moves_with_ir_sequence:
            if not move.posted_before and not move.state == 'posted':
                seq = move._get_journal_sequence()
                move.name = seq.get_next_char(seq.number_next_actual)
        super(AccountMove, self - moves_with_ir_sequence)._compute_name()

    def _post(self, soft=True):
        # OVERRIDE
        moves_with_ir_sequence = self.filtered('journal_id.sequence_id')
        for move in moves_with_ir_sequence:
            seq = move._get_journal_sequence()
            next_name = seq.get_next_char(seq.number_next_actual)
            if not move.posted_before and (move.name == '/' or move.name == next_name):
                # We only compute new name if user didn't manually change the name
                move.name = seq.with_context(ir_sequence_date=move.date).next_by_id()
        return super()._post(soft)

    @api.depends('journal_id', 'date')
    def _compute_highest_name(self):
        # OVERRIDE
        moves_with_ir_sequence = self.filtered('journal_id.sequence_id')
        for move in moves_with_ir_sequence:
            seq = move._get_journal_sequence()
            rec = self.env['account.move'].search([('journal_id.sequence_id', '=', seq.id)], order='name desc', limit=1)
            move.highest_name = rec.name or False
        super(AccountMove, self - moves_with_ir_sequence)._compute_highest_name()
