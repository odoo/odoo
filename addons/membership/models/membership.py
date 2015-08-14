# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp import tools
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
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


class membership_line(osv.osv):
    _name = 'membership.membership_line'
    _description = __doc__

    def _get_partners(self, cr, uid, ids, context=None):
        list_membership_line = []
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.pool.get('res.partner').browse(cr, uid, ids, context=context):
            if partner.member_lines:
                list_membership_line += member_line_obj.search(cr, uid, [('id', 'in', [ l.id for l in partner.member_lines])], context=context)
        return list_membership_line

    def _get_membership_lines(self, cr, uid, ids, context=None):
        list_membership_line = []
        member_line_obj = self.pool.get('membership.membership_line')
        for invoice in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
            if invoice.invoice_line_ids:
                list_membership_line += member_line_obj.search(cr, uid, [('account_invoice_line', 'in', [ l.id for l in invoice.invoice_line_ids])], context=context)
        return list_membership_line

    def _check_membership_date(self, cr, uid, ids, context=None):
        """Check if membership product is not in the past """

        cr.execute('''
         SELECT MIN(ml.date_to - ai.date_invoice)
             FROM membership_membership_line ml
             JOIN account_invoice_line ail ON (
                ml.account_invoice_line = ail.id
                )
            JOIN account_invoice ai ON (
            ai.id = ail.invoice_id)
            WHERE ml.id IN %s''', (tuple(ids),))
        res = cr.fetchall()
        for r in res:
            if r[0] and r[0] < 0:
                return False
        return True

    def _state(self, cr, uid, ids, name, args, context=None):
        """Compute the state lines """
        res = {}
        inv_obj = self.pool.get('account.invoice')
        for line in self.browse(cr, uid, ids, context=context):
            cr.execute('''
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
            fetched = cr.fetchone()
            if not fetched:
                res[line.id] = 'canceled'
                continue
            istate = fetched[0]
            state = 'none'
            if (istate == 'draft') | (istate == 'proforma'):
                state = 'waiting'
            elif istate == 'open':
                state = 'invoiced'
            elif istate == 'paid':
                state = 'paid'
                inv = inv_obj.browse(cr, uid, fetched[1], context=context)
                for payment in inv.payment_ids:
                    if payment.invoice_ids and any(inv.type == 'out_refund' for inv in payment.invoice_ids):
                        state = 'canceled'
            elif istate == 'cancel':
                state = 'canceled'
            res[line.id] = state
        return res

    _columns = {
        'partner': fields.many2one('res.partner', 'Partner', ondelete='cascade', select=1),
        'membership_id': fields.many2one('product.product', string="Membership", required=True),
        'date_from': fields.date('From', readonly=True),
        'date_to': fields.date('To', readonly=True),
        'date_cancel': fields.date('Cancel date'),
        'date': fields.date('Join Date', help="Date on which member has joined the membership"),
        'member_price': fields.float('Membership Fee', digits_compute= dp.get_precision('Product Price'), required=True, help='Amount for the membership'),
        'account_invoice_line': fields.many2one('account.invoice.line', 'Account Invoice line', readonly=True),
        'account_invoice_id': fields.related('account_invoice_line', 'invoice_id', type='many2one', relation='account.invoice', string='Invoice', readonly=True),
        'state': fields.function(_state,
                        string='Membership Status', type='selection',
                        selection=STATE, store = {
                        'account.invoice': (_get_membership_lines, ['state'], 10),
                        'res.partner': (_get_partners, ['membership_state'], 12),
                        }, help="""It indicates the membership status.
                        -Non Member: A member who has not applied for any membership.
                        -Cancelled Member: A member who has cancelled his membership.
                        -Old Member: A member whose membership date has expired.
                        -Waiting Member: A member who has applied for the membership and whose invoice is going to be created.
                        -Invoiced Member: A member whose invoice has been created.
                        -Paid Member: A member who has paid the membership amount."""),
        'company_id': fields.related('account_invoice_line', 'invoice_id', 'company_id', type="many2one", relation="res.company", string="Company", readonly=True, store=True)
    }
    _rec_name = 'partner'
    _order = 'id desc'
    _constraints = [
        (_check_membership_date, 'Error, this membership product is out of date', [])
    ]
