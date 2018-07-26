# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import fields, osv
from openerp import api

class account_analytic_default(osv.osv):
    _name = "account.analytic.default"
    _description = "Analytic Distribution"
    _rec_name = "analytic_id"
    _order = "sequence"
    _columns = {
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of analytic distribution"),
        'analytic_id': fields.many2one('account.analytic.account', 'Analytic Account', domain=[('account_type', '=', 'normal')]),
        'product_id': fields.many2one('product.product', 'Product', ondelete='cascade', help="Select a product which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)"),
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='cascade', help="Select a partner which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)"),
        'user_id': fields.many2one('res.users', 'User', ondelete='cascade', help="Select a user which will use analytic account specified in analytic default."),
        'company_id': fields.many2one('res.company', 'Company', ondelete='cascade', help="Select a company which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)"),
        'date_start': fields.date('Start Date', help="Default start date for this Analytic Account."),
        'date_stop': fields.date('End Date', help="Default end date for this Analytic Account."),
    }

    def account_get(self, cr, uid, product_id=None, partner_id=None, user_id=None, date=None, company_id=None, context=None):
        domain = []
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
        domain += [('product_id','=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
        domain += [('partner_id', '=', False)]
        if company_id:
            domain += ['|', ('company_id', '=', company_id)]
        domain += [('company_id', '=', False)]
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
            if rec.company_id: index += 1
            if rec.user_id: index += 1
            if rec.date_start: index += 1
            if rec.date_stop: index += 1
            if index > best_index:
                res = rec
                best_index = index
        return res


class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    _description = "Invoice Line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(account_invoice_line, self)._onchange_product_id()
        rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.partner_id.id, self._uid,
                                                               time.strftime('%Y-%m-%d'), company_id=self.company_id.id, context=self._context)
        if rec:
            self.account_analytic_id = rec.analytic_id.id
        else:
            self.account_analytic_id = False
        return res

    def _set_additional_fields(self, invoice):
        if not self.account_analytic_id:
            rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.partner_id.id, self._uid,
                                                               time.strftime('%Y-%m-%d'), company_id=self.company_id.id, context=self._context)
            if rec:
                self.account_analytic_id = rec.analytic_id.id
        super(account_invoice_line, self)._set_additional_fields(invoice)

class stock_picking(osv.osv):
    _inherit = "stock.picking"

    def _get_account_analytic_invoice(self, cursor, user, picking, move_line):
        partner_id = picking.partner_id and picking.partner_id.id or False
        rec = self.pool.get('account.analytic.default').account_get(cursor, user, move_line.product_id.id, partner_id, user, time.strftime('%Y-%m-%d'))

        if rec:
            return rec.analytic_id.id

        return super(stock_picking, self)._get_account_analytic_invoice(cursor, user, picking, move_line)


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(sale_order_line, self)._prepare_invoice_line(qty)
        default_analytic_account = self.env['account.analytic.default'].account_get(self.product_id.id, self.order_id.partner_id.id, self.order_id.user_id.id, time.strftime('%Y-%m-%d'))
        if default_analytic_account:
            res.update({'account_analytic_id': default_analytic_account.analytic_id.id})
        return res


class product_product(osv.Model):
    _inherit = 'product.product'
    def _rules_count(self, cr, uid, ids, field_name, arg, context=None):
        Analytic = self.pool['account.analytic.default']
        return {
            product_id: Analytic.search_count(cr, uid, [('product_id', '=', product_id)], context=context)
            for product_id in ids
        }
    _columns = {
        'rules_count': fields.function(_rules_count, string='# Analytic Rules', type='integer'),
    }


class product_template(osv.Model):
    _inherit = 'product.template'
    
    def _rules_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product_tmpl_id in self.browse(cr, uid, ids, context=context):
            res[product_tmpl_id.id] = sum([p.rules_count for p in product_tmpl_id.product_variant_ids])
        return res

    _columns = {
        'rules_count': fields.function(_rules_count, string='# Analytic Rules', type='integer'),
    }


    def action_view_rules(self, cr, uid, ids, context=None):
        products = self._get_products(cr, uid, ids, context=context)
        result = self._get_act_window_dict(cr, uid, 'account_analytic_default.action_product_default_list', context=context)
        result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
        # Remove context so it is not going to filter on product_id with active_id of template
        result['context'] = "{}"
        return result


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
