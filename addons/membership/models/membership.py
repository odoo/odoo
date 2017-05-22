# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp

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

    partner = fields.Many2one('res.partner', string='Partner', ondelete='cascade', index=True)
    membership_id = fields.Many2one('product.product', string="Membership", required=True)
    date_from = fields.Date(string='From', readonly=True)
    date_to = fields.Date(string='To', readonly=True)
    date_cancel = fields.Date(string='Cancel date')
    date = fields.Date(string='Join Date',
        help="Date on which member has joined the membership")
    member_price = fields.Float(string='Membership Fee',
        digits=dp.get_precision('Product Price'), required=True,
        help='Amount for the membership')
    account_invoice_line = fields.Many2one('account.invoice.line', string='Account Invoice line', readonly=True, ondelete='cascade')
    account_invoice_id = fields.Many2one('account.invoice', related='account_invoice_line.invoice_id', string='Invoice', readonly=True)
    company_id = fields.Many2one('res.company', related='account_invoice_line.invoice_id.company_id', string="Company", readonly=True, store=True)
    state = fields.Selection(STATE, compute='_compute_state', string='Membership Status', store=True,
        help="It indicates the membership status.\n"
             "-Non Member: A member who has not applied for any membership.\n"
             "-Cancelled Member: A member who has cancelled his membership.\n"
             "-Old Member: A member whose membership date has expired.\n"
             "-Waiting Member: A member who has applied for the membership and whose invoice is going to be created.\n"
             "-Invoiced Member: A member whose invoice has been created.\n"
             "-Paid Member: A member who has paid the membership amount.")

    @api.depends('account_invoice_line.invoice_id.state',
                 'account_invoice_line.invoice_id.payment_ids',
                 'account_invoice_line.invoice_id.payment_ids.invoice_ids.type')
    def _compute_state(self):
        """Compute the state lines """
        Invoice = self.env['account.invoice']
        for line in self:
            self._cr.execute('''
            SELECT i.state, i.id FROM
            account_invoice i
            WHERE
            i.id = (
                SELECT l.invoice_id FROM
                account_invoice_line l WHERE
                l.id = (
                    SELECT  ml.account_invoice_line FROM
                    membership_membership_line ml WHERE
                    ml.id = %s
                    )
                )
            ''', (line.id,))
            fetched = self._cr.fetchone()
            if not fetched:
                line.state = 'canceled'
                continue
            istate = fetched[0]
            if istate == 'draft':
                line.state = 'waiting'
            elif istate == 'open':
                line.state = 'invoiced'
            elif istate == 'paid':
                line.state = 'paid'
                invoices = Invoice.browse(fetched[1]).payment_ids.mapped('invoice_ids')
                if invoices.filtered(lambda invoice: invoice.type == 'out_refund'):
                    line.state = 'canceled'
            elif istate == 'cancel':
                line.state = 'canceled'
            else:
                line.state = 'none'
