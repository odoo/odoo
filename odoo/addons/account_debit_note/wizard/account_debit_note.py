# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountDebitNote(models.TransientModel):
    """
    Add Debit Note wizard: when you want to correct an invoice with a positive amount.
    Opposite of a Credit Note, but different from a regular invoice as you need the link to the original invoice.
    In some cases, also used to cancel Credit Notes
    """
    _name = 'account.debit.note'
    _description = 'Add Debit Note wizard'

    move_ids = fields.Many2many('account.move', 'account_move_debit_move', 'debit_id', 'move_id',
                                domain=[('state', '=', 'posted')])
    date = fields.Date(string='Debit Note Date', default=fields.Date.context_today, required=True)
    reason = fields.Char(string='Reason')
    journal_id = fields.Many2one('account.journal', string='Use Specific Journal',
                                 help='If empty, uses the journal of the journal entry to be debited.')
    copy_lines = fields.Boolean("Copy Lines",
                                help="In case you need to do corrections for every line, it can be in handy to copy them.  "
                                     "We won't copy them for debit notes from credit notes. ")
    # computed fields
    move_type = fields.Char(compute="_compute_from_moves")
    journal_type = fields.Char(compute="_compute_from_moves")
    country_code = fields.Char(related='move_ids.company_id.country_id.code')

    @api.model
    def default_get(self, fields):
        res = super(AccountDebitNote, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']
        if any(move.state != "posted" for move in move_ids):
            raise UserError(_('You can only debit posted moves.'))
        elif any(move.debit_origin_id for move in move_ids):
            raise UserError(_("You can't make a debit note for an invoice that is already linked to a debit note."))
        elif any(move.move_type not in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'] for move in move_ids):
            raise UserError(_("You can make a debit note only for a Customer Invoice, a Customer Credit Note, a Vendor Bill or a Vendor Credit Note."))
        res['move_ids'] = [(6, 0, move_ids.ids)]
        return res

    @api.depends('move_ids')
    def _compute_from_moves(self):
        for record in self:
            move_ids = record.move_ids
            record.move_type = move_ids[0].move_type if len(move_ids) == 1 or not any(m.move_type != move_ids[0].move_type for m in move_ids) else False
            record.journal_type = record.move_type in ['in_refund', 'in_invoice'] and 'purchase' or 'sale'

    def _prepare_default_values(self, move):
        if move.move_type in ('in_refund', 'out_refund'):
            type = 'in_invoice' if move.move_type == 'in_refund' else 'out_invoice'
        else:
            type = move.move_type
        default_values = {
                'ref': '%s, %s' % (move.name, self.reason) if self.reason else move.name,
                'date': self.date or move.date,
                'invoice_date': move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
                'journal_id': self.journal_id and self.journal_id.id or move.journal_id.id,
                'invoice_payment_term_id': None,
                'debit_origin_id': move.id,
                'move_type': type,
            }
        if not self.copy_lines or move.move_type in [('in_refund', 'out_refund')]:
            default_values['line_ids'] = [(5, 0, 0)]
        return default_values

    def create_debit(self):
        self.ensure_one()
        new_moves = self.env['account.move']
        for move in self.move_ids.with_context(include_business_fields=True): #copy sale/purchase links
            default_values = self._prepare_default_values(move)
            new_move = move.copy(default=default_values)
            move_msg = _("This debit note was created from: %s", move._get_html_link())
            new_move.message_post(body=move_msg)
            new_moves |= new_move

        action = {
            'name': _('Debit Notes'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'default_move_type': default_values['move_type']},
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
