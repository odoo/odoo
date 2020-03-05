# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _name = 'account.move.reversal'
    _description = 'Account Move Reversal'
    _check_company_auto = True

    move_ids = fields.Many2many('account.move', 'account_move_reversal_move', 'reversal_id', 'move_id', domain=[('state', '=', 'posted')])
    new_move_ids = fields.Many2many('account.move', 'account_move_reversal_new_move', 'reversal_id', 'new_move_id')
    date_mode = fields.Selection(selection=[
            ('custom', 'Specific'),
            ('entry', 'Journal Entry Date')
    ], required=True, default='custom')
    date = fields.Date(string='Reversal date', default=fields.Date.context_today)
    reason = fields.Char(string='Reason')
    refund_method = fields.Selection(selection=[
            ('refund', 'Partial Refund'),
            ('cancel', 'Full Refund'),
            ('modify', 'Full refund and new draft invoice')
        ], string='Credit Method', required=True,
        help='Choose how you want to credit this invoice. You cannot "modify" nor "cancel" if the invoice is already reconciled.')
    journal_id = fields.Many2one('account.journal', string='Use Specific Journal', help='If empty, uses the journal of the journal entry to be reversed.', check_company=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True)

    # computed fields
    residual = fields.Monetary(compute="_compute_from_moves")
    currency_id = fields.Many2one('res.currency', compute="_compute_from_moves")
    move_type = fields.Char(compute="_compute_from_moves")

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversal, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']

        if any(move.state != "posted" for move in move_ids):
            raise UserError(_('You can only reverse posted moves.'))
        res['company_id'] = move_ids.company_id.id or self.env.company.id
        res['move_ids'] = [(6, 0, move_ids.ids)]
        res['refund_method'] = (len(move_ids) > 1 or move_ids.move_type == 'entry') and 'cancel' or 'refund'
        return res

    @api.depends('move_ids')
    def _compute_from_moves(self):
        for record in self:
            move_ids = record.move_ids
            record.residual = len(move_ids) == 1 and move_ids.amount_residual or 0
            record.currency_id = len(move_ids.currency_id) == 1 and move_ids.currency_id or False
            record.move_type = move_ids.move_type if len(move_ids) == 1 else (any(move.move_type in ('in_invoice', 'out_invoice') for move in move_ids) and 'some_invoice' or False)

    def _prepare_default_reversal(self, move):
        reverse_date = self.date if self.date_mode == 'custom' else move.date
        return {
            'ref': _('Reversal of: %s, %s') % (move.name, self.reason) if self.reason else _('Reversal of: %s') % (move.name),
            'date': reverse_date,
            'invoice_date': move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
            'journal_id': self.journal_id and self.journal_id.id or move.journal_id.id,
            'invoice_payment_term_id': None,
            'invoice_user_id': move.invoice_user_id.id,
            'auto_post': True if reverse_date > fields.Date.context_today(self) else False,
        }

    def reverse_moves(self):
        self.ensure_one()
        moves = self.move_ids

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        # Handle reverse method.
        if self.refund_method == 'cancel':
            if any([vals.get('auto_post', False) for vals in default_values_list]):
                new_moves = moves._reverse_moves(default_values_list)
            else:
                new_moves = moves._reverse_moves(default_values_list, cancel=True)
        elif self.refund_method == 'modify':
            moves._reverse_moves(default_values_list, cancel=True)
            moves_vals_list = []
            for move in moves.with_context(include_business_fields=True):
                moves_vals_list.append(move.copy_data({
                    'date': self.date if self.date_mode == 'custom' else move.date,
                })[0])
            new_moves = self.env['account.move'].create(moves_vals_list)
        elif self.refund_method == 'refund':
            new_moves = moves._reverse_moves(default_values_list)
        else:
            return

        self.new_move_ids = new_moves

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
