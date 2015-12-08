# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import osv


class stock_picking(osv.osv):
    _inherit = "stock.picking"

    def _get_account_analytic_invoice(self, cursor, user, picking, move_line):
        partner_id = picking.partner_id and picking.partner_id.id or False
        rec = self.pool.get('account.analytic.default').account_get(cursor, user, move_line.product_id.id, partner_id, user, time.strftime('%Y-%m-%d'))

        if rec:
            return rec.analytic_id.id

        return super(stock_picking, self)._get_account_analytic_invoice(cursor, user, picking, move_line)


class stock_move(osv.Model):
    _inherit = 'stock.move'

    def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
        # It will set the default analtyic account on the invoice line
        partner_id = self.pool['account.invoice'].browse(cr, uid, invoice_line_vals.get('invoice_id'), context=context).partner_id.id
        if 'account_analytic_id' not in invoice_line_vals or not invoice_line_vals.get('account_analytic_id'):
            rec = self.pool['account.analytic.default'].account_get(cr, uid, move.product_id.id, partner_id, uid, time.strftime('%Y-%m-%d'), company_id=move.company_id.id, context=context)
            if rec:
                invoice_line_vals.update({'account_analytic_id': rec.analytic_id.id})
        res = super(stock_move, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
        return res
