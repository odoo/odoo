# -*- coding: utf-8 -*-
###############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from openerp.osv import fields, osv

class account_analytic_default(osv.osv):
    _name = "account.analytic.default"
    _description = "Analytic Distribution"
    _rec_name = "analytic_id"
    _order = "sequence"
    _columns = {
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of analytic distribution"),
        'analytic_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'product_id': fields.many2one('product.product', 'Product', ondelete='cascade', help="Select a product which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)"),
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='cascade', help="Select a partner which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)"),
        'user_id': fields.many2one('res.users', 'User', ondelete='cascade', help="Select a user which will use analytic account specified in analytic default."),
        'company_id': fields.many2one('res.company', 'Company', ondelete='cascade', help="Select a company which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)"),
        'date_start': fields.date('Start Date', help="Default start date for this Analytic Account."),
        'date_stop': fields.date('End Date', help="Default end date for this Analytic Account."),
    }

    def account_get(self, cr, uid, product_id=None, partner_id=None, user_id=None, date=None, context=None):
        domain = []
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
        domain += [('product_id','=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
        domain += [('partner_id', '=', False)]
        if user_id:
            domain += ['|',('user_id', '=', user_id)]
        domain += [('user_id','=', False)]
        if date:
            domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
            domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
        best_index = -1
        res = False
        for rec in self.browse(cr, uid, self.search(cr, uid, domain, context=context), context=context):
            index = 0
            if rec.product_id: index += 1
            if rec.partner_id: index += 1
            if rec.user_id: index += 1
            if rec.date_start: index += 1
            if rec.date_stop: index += 1
            if index > best_index:
                res = rec
                best_index = index
        return res

account_analytic_default()

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    _description = "Invoice Line"

    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, currency_id=False, context=None, company_id=None):
        res_prod = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, currency_id=currency_id, context=context, company_id=company_id)
        rec = self.pool.get('account.analytic.default').account_get(cr, uid, product, partner_id, uid, time.strftime('%Y-%m-%d'), context=context)
        if rec:
            res_prod['value'].update({'account_analytic_id': rec.analytic_id.id})
        else:
            res_prod['value'].update({'account_analytic_id': False})
        return res_prod

account_invoice_line()


class stock_picking(osv.osv):
    _inherit = "stock.picking"

    def _get_account_analytic_invoice(self, cursor, user, picking, move_line):
        partner_id = picking.partner_id and picking.partner_id.id or False
        rec = self.pool.get('account.analytic.default').account_get(cursor, user, move_line.product_id.id, partner_id , user, time.strftime('%Y-%m-%d'), context={})

        if rec:
            return rec.analytic_id.id

        return super(stock_picking, self)._get_account_analytic_invoice(cursor, user, picking, move_line)

stock_picking()

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    # Method overridden to set the analytic account by default on criterion match
    def invoice_line_create(self, cr, uid, ids, context=None):
        create_ids = super(sale_order_line, self).invoice_line_create(cr, uid, ids, context=context)
        if not ids:
            return create_ids
        sale_line = self.browse(cr, uid, ids[0], context=context)
        inv_line_obj = self.pool.get('account.invoice.line')
        anal_def_obj = self.pool.get('account.analytic.default')

        for line in inv_line_obj.browse(cr, uid, create_ids, context=context):
            rec = anal_def_obj.account_get(cr, uid, line.product_id.id, sale_line.order_id.partner_id.id, sale_line.order_id.user_id.id, time.strftime('%Y-%m-%d'), context=context)

            if rec:
                inv_line_obj.write(cr, uid, [line.id], {'account_analytic_id': rec.analytic_id.id}, context=context)
        return create_ids

sale_order_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
