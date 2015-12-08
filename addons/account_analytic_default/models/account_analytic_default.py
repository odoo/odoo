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
