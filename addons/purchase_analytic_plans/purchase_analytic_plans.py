# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class purchase_order_line(osv.osv):
    _name='purchase.order.line'
    _inherit='purchase.order.line'
    _columns = {
         'analytics_id':fields.many2one('account.analytic.plan.instance','Analytic Distribution'),
    }


class purchase_order(osv.osv):
    _name='purchase.order'
    _inherit='purchase.order'

    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        res = super(purchase_order, self)._prepare_inv_line(cr, uid, account_id, order_line, context=context)
        res['analytics_id'] = order_line.analytics_id.id
        return res
