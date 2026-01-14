# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

STATE = [
    ('none', 'Non Member'),
    ('canceled', 'Cancelled Member'),
    ('old', 'Old Member'),
    ('waiting', 'Waiting Member'),
    ('invoiced', 'Invoiced Member'),
    ('free', 'Free Member'),
    ('paid', 'Paid Member'),
]


class MembershipLine(models.Model):
    _name = 'membership.membership_line'
    _rec_name = 'partner'
    _order = 'id desc'
    _description = 'Membership Line'

    partner = fields.Many2one('res.partner', string='Partner', ondelete='cascade', index=True)
    membership_id = fields.Many2one('product.product', string="Membership", required=True)
    date_from = fields.Date(string='From', readonly=True)
    date_to = fields.Date(string='To', readonly=True)
    date_cancel = fields.Date(string='Cancel date')
    date = fields.Date(string='Join Date',
        help="Date on which member has joined the membership")
    member_price = fields.Float(string='Membership Fee',
        min_display_digits='Product Price', required=True,
        help='Amount for the membership')
    account_invoice_line = fields.Many2one('account.move.line', string='Account Invoice line', readonly=True, ondelete='cascade')
    account_invoice_id = fields.Many2one('account.move', related='account_invoice_line.move_id', string='Invoice', readonly=True)
    company_id = fields.Many2one('res.company', related='account_invoice_line.move_id.company_id', string="Company", readonly=True, store=True)
    state = fields.Selection(STATE, compute='_compute_state', string='Membership Status', store=True,
        help="It indicates the membership status.\n"
             "-Non Member: A member who has not applied for any membership.\n"
             "-Cancelled Member: A member who has cancelled his membership.\n"
             "-Old Member: A member whose membership date has expired.\n"
             "-Waiting Member: A member who has applied for the membership and whose invoice is going to be created.\n"
             "-Invoiced Member: A member whose invoice has been created.\n"
             "-Paid Member: A member who has paid the membership amount.")

    @api.depends('account_invoice_id.state',
                 'account_invoice_id.amount_residual',
                 'account_invoice_id.payment_state')
    def _compute_state(self):
        """Compute the state lines """
        if not self:
            return

        self._cr.execute('''
            SELECT reversed_entry_id, COUNT(id)
            FROM account_move
            WHERE reversed_entry_id IN %s
            GROUP BY reversed_entry_id
        ''', [tuple(self.mapped('account_invoice_id.id'))])
        reverse_map = dict(self._cr.fetchall())
        for line in self:
            move_state = line.account_invoice_id.state
            payment_state = line.account_invoice_id.payment_state

            line.state = 'none'
            if move_state == 'draft':
                line.state = 'waiting'
            elif move_state == 'posted':
                if payment_state == 'paid':
                    if reverse_map.get(line.account_invoice_id.id):
                        line.state = 'canceled'
                    else:
                        line.state = 'paid'
                elif payment_state == 'in_payment':
                    line.state = 'paid'
                elif payment_state in ('not_paid', 'partial'):
                    line.state = 'invoiced'
            elif move_state == 'cancel':
                line.state = 'canceled'
