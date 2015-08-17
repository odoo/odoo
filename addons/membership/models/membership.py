# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, models, fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError

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
    _description = __doc__
    _rec_name = 'partner_id'
    _order = 'id desc'
    partner_id = fields.Many2one('res.partner', 'Partner', ondelete='cascade', index=1)
    membership_id = fields.Many2one('product.product', string="Membership", required=True)
    date_from = fields.Date('From', readonly=True)
    date_to = fields.Date('To', readonly=True)
    date_cancel = fields.Date('Cancel date')
    date = fields.Date('Join Date', help="Date on which member has joined the membership")
    member_price = fields.Float('Membership Fee', digits=dp.get_precision('Product Price'), required=True, help='Amount for the membership')
    account_invoice_line_id = fields.Many2one('account.invoice.line', 'Account Invoice line', readonly=True)
    account_invoice_id = fields.Many2one('account.invoice', related='account_invoice_line_id.invoice_id', string='Invoice', readonly=True)
    state = fields.Selection(compute='_compute_state', string='Membership Status', selection=STATE, store=True, help="""It indicates the membership status.
                    -Non Member: A member who has not applied for any membership.
                    -Cancelled Member: A member who has cancelled his membership.
                    -Old Member: A member whose membership date has expired.
                    -Waiting Member: A member who has applied for the membership and whose invoice is going to be created.
                    -Invoiced Member: A member whose invoice has been created.
                    -Paid Member: A member who has paid the membership amount.""")
    company_id = fields.Many2one('res.company', related='account_invoice_line_id.invoice_id.company_id', string="Company", readonly=True, store=True)

    @api.depends('account_invoice_id.state', 'partner_id.membership_state')
    def _compute_state(self):
        """Compute the state lines """
        AccountInvoice = self.env['account.invoice']
        self.env.cr.execute('''
            SELECT i.state, i.id FROM
            account_invoice i
            WHERE
            i.id IN (
                SELECT l.invoice_id FROM
                account_invoice_line l WHERE
                l.id IN (
                    SELECT  ml.account_invoice_line_id FROM
                    membership_membership_line ml WHERE
                    ml.id IN %s
                    )
                )
            ''', (tuple(self.ids), ))
        result = self.env.cr.dictfetchall()
        for line in self:
            fetched = filter(lambda x: x['id'] == line.account_invoice_line_id.id, result)
            if not fetched:
                line.state = 'canceled'
                continue
            istate = fetched[0]['state']
            state = 'none'
            if (istate == 'draft') | (istate == 'proforma'):
                state = 'waiting'
            elif istate == 'open':
                state = 'invoiced'
            elif istate == 'paid':
                state = 'paid'
                inv = AccountInvoice.browse(fetched[0]['id'])
                for payment in inv.payment_ids:
                    if payment.invoice_ids and any(inv.type == 'out_refund' for inv in payment.invoice_ids):
                        state = 'canceled'
            elif istate == 'cancel':
                state = 'canceled'
            line.state = state

    @api.multi
    @api.constrains('date_to')
    def _check_membership_date(self):
        """Check if membership product is not in the past """

        self.env.cr.execute('''
         SELECT MIN(ml.date_to - ai.date_invoice)
             FROM membership_membership_line ml
             JOIN account_invoice_line ail ON (
                ml.account_invoice_line_id = ail.id
                )
            JOIN account_invoice ai ON (
            ai.id = ail.invoice_id)
            WHERE ml.id IN %s''', (tuple(self.ids),))
        records = self.env.cr.fetchall()
        for record in records:
            if record[0] and record[0] < 0:
                raise UserError(_('Error, this membership product is out of date'))
        return