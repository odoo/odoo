# -*- coding: utf-8 -*-
##############################################################################
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

from openerp.osv import fields, osv
import time


class purchase_order_line(osv.osv):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'
    _columns = {
        'analytics_id': fields.many2one('account.analytic.plan.instance', 'Analytic Distribution'),
    }

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
                            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
                            name=False, price_unit=False, state='draft', context=None):

        if context is None:
            context = {}

        res = super(purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
                                                                   partner_id, date_order, fiscal_position_id, date_planned,
                                                                   name, price_unit, state, context=context)

        anal_def_obj = self.pool.get('account.analytic.default')

        rec = anal_def_obj.account_get(
            cr, uid, product_id, partner_id, uid, time.strftime('%Y-%m-%d'), context=context)

        if rec:
            res['value'].update({'analytics_id': rec.analytics_id.id})

        return res


class purchase_order(osv.osv):
    _name = 'purchase.order'
    _inherit = 'purchase.order'

    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        res = super(purchase_order, self)._prepare_inv_line(
            cr, uid, account_id, order_line, context=context)
        res['analytics_id'] = order_line.analytics_id.id
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
