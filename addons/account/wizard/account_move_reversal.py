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
    date = fields.Date(string='Reversal date', default=fields.Date.context_today)
    reason = fields.Char(string='Reason displayed on Credit Note')
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        required=True,
        compute='_compute_journal_id',
        readonly=False,
        store=True,
        check_company=True,
        help='If empty, uses the journal of the journal entry to be reversed.',
    )
    company_id = fields.Many2one('res.company', required=True, readonly=True)
    available_journal_ids = fields.Many2many('account.journal', compute='_compute_available_journal_ids')
    country_code = fields.Char(related='company_id.country_id.code')

    # computed fields
    residual = fields.Monetary(compute="_compute_from_moves")
    currency_id = fields.Many2one('res.currency', compute="_compute_from_moves")
    move_type = fields.Char(compute="_compute_from_moves")

    @api.depends('move_ids')
    def _compute_journal_id(self):
        for record in self:
            if record.journal_id:
                record.journal_id = record.journal_id
            else:
                journals = record.move_ids.journal_id.filtered(lambda x: x.active)
                record.journal_id = journals[0] if journals else None

    @api.depends('move_ids')
    def _compute_available_journal_ids(self):
        for record in self:
            if record.move_ids:
                record.available_journal_ids = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(record.company_id),
                    ('type', 'in', record.move_ids.journal_id.mapped('type')),
                ])
            else:
                record.available_journal_ids = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(record.company_id),
                ])

    @api.constrains('journal_id', 'move_ids')
    def _check_journal_type(self):
        for record in self:
            if record.journal_id.type not in record.move_ids.journal_id.mapped('type'):
                raise UserError(_('Journal should be the same type as the reversed entry.'))

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversal, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']

        if len(move_ids.company_id) > 1:
            raise UserError(_("All selected moves for reversal must belong to the same company."))

        if any(move.state != "posted" for move in move_ids):
            raise UserError(_('You can only reverse posted moves.'))
        if 'company_id' in fields:
            res['company_id'] = move_ids.company_id.id or self.env.company.id
        if 'move_ids' in fields:
            res['move_ids'] = [(6, 0, move_ids.ids)]
        return res

    @api.depends('move_ids')
    def _compute_from_moves(self):
        for record in self:
            move_ids = record.move_ids._origin
            record.residual = len(move_ids) == 1 and move_ids.amount_residual or 0
            record.currency_id = len(move_ids.currency_id) == 1 and move_ids.currency_id or False
            record.move_type = move_ids.move_type if len(move_ids) == 1 else (any(move.move_type in ('in_invoice', 'out_invoice') for move in move_ids) and 'some_invoice' or False)

    def _prepare_default_reversal(self, move):
        reverse_date = self.date
        mixed_payment_term = move.invoice_payment_term_id.id if move.invoice_payment_term_id.early_pay_discount_computation == 'mixed' else None
        return {
            'ref': _('Reversal of: %(move_name)s, %(reason)s', move_name=move.name, reason=self.reason)
                   if self.reason
                   else _('Reversal of: %s', move.name),
            'date': reverse_date,
            'invoice_date_due': reverse_date,
            'invoice_date': move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
            'journal_id': self.journal_id.id,
            'invoice_payment_term_id': mixed_payment_term,
            'invoice_user_id': move.invoice_user_id.id,
            'auto_post': 'at_date' if reverse_date > fields.Date.context_today(self) else 'no',
        }

    def reverse_moves(self, is_modify=False):
        self.ensure_one()
        moves = self.move_ids

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = default_vals.get('auto_post') != 'no'
            is_cancel_needed = not is_auto_post and (is_modify or self.move_type == 'entry')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)
            moves._message_log_batch(
                bodies={move.id: _('This entry has been %s', reverse._get_html_link(title=_("reversed"))) for move, reverse in zip(moves, new_moves)}
            )

            if is_modify:
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    data = move.copy_data({'date': self.date})[0]
                    data['line_ids'] = [line for line in data['line_ids'] if line[2]['display_type'] == 'product']
                    moves_vals_list.append(data)
                new_moves = self.env['account.move'].create(moves_vals_list)

            moves_to_redirect |= new_moves

        self.new_move_ids = moves_to_redirect

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
                'context': {'default_move_type':  moves_to_redirect.move_type},
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
            if len(set(moves_to_redirect.mapped('move_type'))) == 1:
                action['context'] = {'default_move_type':  moves_to_redirect.mapped('move_type').pop()}
        return action

    def refund_moves(self):
        return self.reverse_moves(is_modify=False)

    def modify_moves(self):
        return self.reverse_moves(is_modify=True)
