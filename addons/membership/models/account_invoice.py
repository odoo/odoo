# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import fields, osv


class Invoice(osv.osv):
    _inherit = 'account.invoice'

    def action_cancel(self, cr, uid, ids, context=None):
        '''Create a 'date_cancel' on the membership_line object'''
        member_line_obj = self.pool.get('membership.membership_line')
        today = time.strftime('%Y-%m-%d')
        for invoice in self.browse(cr, uid, ids, context=context):
            mlines = member_line_obj.search(cr, uid,
                    [('account_invoice_line', 'in',
                        [l.id for l in invoice.invoice_line_ids])])
            member_line_obj.write(cr, uid, mlines, {'date_cancel': today})
        return super(Invoice, self).action_cancel(cr, uid, ids, context=context)

    # TODO master: replace by ondelete='cascade'
    def unlink(self, cr, uid, ids, context=None):
        member_line_obj = self.pool.get('membership.membership_line')
        for invoice in self.browse(cr, uid, ids, context=context):
            mlines = member_line_obj.search(cr, uid,
                    [('account_invoice_line', 'in',
                        [l.id for l in invoice.invoice_line_ids])])
            member_line_obj.unlink(cr, uid, mlines, context=context)
        return super(Invoice, self).unlink(cr, uid, ids, context=context)


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    def write(self, cr, uid, ids, vals, context=None):
        """Overrides orm write method
        """
        member_line_obj = self.pool.get('membership.membership_line')
        res = super(account_invoice_line, self).write(cr, uid, ids, vals, context=context)
        for line in self.browse(cr, uid, ids, context=context):
            if line.invoice_id.type == 'out_invoice':
                ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line', '=', line.id)], context=context)
                if line.product_id and line.product_id.membership and not ml_ids:
                    # Product line has changed to a membership product
                    date_from = line.product_id.membership_date_from
                    date_to = line.product_id.membership_date_to
                    if line.invoice_id.date_invoice > date_from and line.invoice_id.date_invoice < date_to:
                        date_from = line.invoice_id.date_invoice
                    member_line_obj.create(cr, uid, {
                                    'partner': line.invoice_id.partner_id.id,
                                    'membership_id': line.product_id.id,
                                    'member_price': line.price_unit,
                                    'date': time.strftime('%Y-%m-%d'),
                                    'date_from': date_from,
                                    'date_to': date_to,
                                    'account_invoice_line': line.id,
                                    }, context=context)
                if line.product_id and not line.product_id.membership and ml_ids:
                    # Product line has changed to a non membership product
                    member_line_obj.unlink(cr, uid, ml_ids, context=context)
        return res

    # TODO master: replace by ondelete='cascade'
    def unlink(self, cr, uid, ids, context=None):
        """Remove Membership Line Record for Account Invoice Line
        """
        member_line_obj = self.pool.get('membership.membership_line')
        for id in ids:
            ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line', '=', id)], context=context)
            member_line_obj.unlink(cr, uid, ml_ids, context=context)
        return super(account_invoice_line, self).unlink(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        """Overrides orm create method
        """
        member_line_obj = self.pool.get('membership.membership_line')
        result = super(account_invoice_line, self).create(cr, uid, vals, context=context)
        line = self.browse(cr, uid, result, context=context)
        if line.invoice_id.type == 'out_invoice':
            ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line', '=', line.id)], context=context)
            if line.product_id and line.product_id.membership and not ml_ids:
                # Product line is a membership product
                date_from = line.product_id.membership_date_from
                date_to = line.product_id.membership_date_to
                if line.invoice_id.date_invoice > date_from and line.invoice_id.date_invoice < date_to:
                    date_from = line.invoice_id.date_invoice
                values = {
                            'partner': line.invoice_id.partner_id and line.invoice_id.partner_id.id or False,
                            'membership_id': line.product_id.id,
                            'member_price': line.price_unit,
                            'date': time.strftime('%Y-%m-%d'),
                            'date_from': date_from,
                            'date_to': date_to,
                            'account_invoice_line': line.id,
                        }
                member_line_obj.create(cr, uid, values, context=context)
        return result
