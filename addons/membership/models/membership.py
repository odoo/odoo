# -*- coding: utf-8 -*-

from openerp import api, fields, models
from openerp.addons import decimal_precision as dp


class membership_line(models.Model):
    _name = 'membership.line'  # TDE-MIGR: was membership.membership_line
    _description = __doc__
    _rec_name = 'partner_id'
    _order = 'id desc'

    @api.multi
    def _compute_state(self):
        for membership in self:
            if not membership.account_invoice_id:
                membership.state == 'canceled'
            elif membership.account_invoice_id.state in ['draft', 'proforma']:
                membership.state = 'waiting'
            elif membership.account_invoice_id.state == 'open':
                membership.state = 'invoiced'
            elif membership.account_invoice_id.state == 'paid':
                membership.state = 'paid'
                # inv = inv_obj.browse(cr, uid, fetched[1], context=context)
                # for payment in inv.payment_ids:
                #     if payment.invoice and payment.invoice.type == 'out_refund':
                #         state = 'canceled'
            elif membership.account_invoice_id.istate == 'cancel':
                membership.state = 'canceled'
            else:
                membership.state = 'none'

    partner_id = fields.Many2one('res.partner', 'Partner', ondelete='cascade', select=1, oldname='partner')
    membership_id = fields.Many2one('product.product', string="Membership", required=True, select=1)
    date_from = fields.Date('From', readonly=True)
    date_to = fields.Date('To', readonly=True)
    date_cancel = fields.Date('Cancel date')
    date = fields.Date('Join Date', help="Date on which member has joined the membership")
    member_price = fields.Float('Membership Fee', digits_compute=dp.get_precision('Product Price'), required=True, help='Amount for the membership')
    account_invoice_line_id = fields.Many2one('account.invoice.line', 'Account Invoice line', readonly=True, oldname='account_invoice_line')
    account_invoice_id = fields.Many2one('account.invoice', related='account_invoice_line_id.invoice_id', string='Invoice')
    state = fields.Selection(
        [('none', 'Non Member'), ('canceled', 'Cancelled Member'),
         ('old', 'Old Member'), ('waiting', 'Waiting Member'),
         ('invoiced', 'Invoiced Member'), ('free', 'Free Member'),
         ('paid', 'Paid Member')],
        string='Membership Status',
        compute='_compute_state',
        help="""Indicates the membership status.
                -Non Member: A member who has not applied for any membership.
                -Cancelled Member: A member who has cancelled his membership.
                -Old Member: A member whose membership date has expired.
                -Waiting Member: A member who has applied for the membership and whose invoice is going to be created.
                -Invoiced Member: A member whose invoice has been created.
                -Paid Member: A member who has paid the membership amount.""")
    company_id = fields.Many2one('res.company', related='account_invoice_line_id.invoice_id.company_id', string="Company", readonly=True)

    @api.one
    # @api.constrains('seats_max', 'seats_available')
    def _check_date(self):
        # """Check if membership product is not in the past
        # @param self: The object pointer
        # @param cr: the current row, from the database cursor,
        # @param uid: the current user’s ID for security checks,
        # @param ids: List of Membership Line IDs
        # @param context: A standard dictionary for contextual values
        # """

        # cr.execute('''
        #  SELECT MIN(ml.date_to - ai.date_invoice)
        #      FROM membership_membership_line ml
        #      JOIN account_invoice_line ail ON (
        #         ml.account_invoice_line = ail.id
        #         )
        #     JOIN account_invoice ai ON (
        #     ai.id = ail.invoice_id)
        #     WHERE ml.id IN %s''', (tuple(ids),))
        # res = cr.fetchall()
        # for r in res:
        #     if r[0] and r[0] < 0:
        #         return False
        return True
