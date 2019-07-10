# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _name = 'account.move.reversal'
    _description = 'Account Move Reversal'

    @api.model
    def _get_default_move(self):
        if self._context.get('active_id'):
            move = self.env['account.move'].browse(self._context['active_id'])
            if move.state != 'posted' or move.type in ('out_refund', 'in_refund'):
                raise UserError(_('Only posted journal entries being not already a refund can be reversed.'))
            return move
        return self.env['account.move']

    @api.model
    def _get_default_reason(self):
        move = self._get_default_move()
        return move and move.invoice_payment_ref or False

    move_id = fields.Many2one('account.move', string='Journal Entry',
        default=_get_default_move,
        domain=[('state', '=', 'posted'), ('type', 'not in', ('out_refund', 'in_refund'))])
    date = fields.Date(string='Reversal date', default=fields.Date.context_today, required=True)
    reason = fields.Char(string='Reason', default=_get_default_reason)
    refund_method = fields.Selection(selection=[
            ('refund', 'Create a draft credit note (partial refunding)'),
            ('cancel', 'Cancel: create credit note and reconcile (full refunding)'),
            ('modify', 'Create credit note, reconcile and create a new draft invoice (cancel)')
        ], default='refund', string='Credit Method', required=True,
        help='Choose how you want to credit this invoice. You cannot "modify" nor "cancel" if the invoice is already reconciled.')
    journal_id = fields.Many2one('account.journal', string='Use Specific Journal', help='If empty, uses the journal of the journal entry to be reversed.')

    # related fields
    residual = fields.Monetary(related='move_id.amount_residual')
    currency_id = fields.Many2one(related='move_id.currency_id')
    move_type = fields.Selection(related='move_id.type')

    def reverse_moves(self):
        moves = self.move_id or self.env['account.move'].browse(self._context['active_ids'])

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append({
                'ref': _('Reversal of: %s') % move.name,
                'invoice_payment_ref': self.reason,
                'date': self.date or move.date,
                'invoice_date': move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
                'journal_id': self.journal_id and self.journal_id.id or move.journal_id.id,
            })

        # Handle reverse method.
        if self.refund_method == 'cancel' or (moves and moves[0].type == 'entry'):
            new_moves = moves._reverse_moves(default_values_list, cancel=True)
        elif self.refund_method == 'modify':
            new_moves = moves._reverse_moves(default_values_list, cancel=True)
            moves_vals_list = []
            for move in moves.with_context(include_business_fields=True):
                moves_vals_list.append(move.copy_data({
                    'invoice_payment_ref': move.name,
                    'date': self.date or move.date,
                })[0])
            new_moves = moves.create(moves_vals_list)
        elif self.refund_method == 'refund':
            new_moves = moves._reverse_moves(default_values_list)
        else:
            return

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(new_moves) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': new_moves.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', new_moves.ids)],
            })
        return action
