# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class product_price_list(osv.osv_memory):
    _name = 'product.price_list'
    _description = 'Price List'

    _columns = {
        'price_list': fields.many2one('product.pricelist', 'PriceList', required=True),
        'qty1': fields.integer('Quantity-1'),
        'qty2': fields.integer('Quantity-2'),
        'qty3': fields.integer('Quantity-3'),
        'qty4': fields.integer('Quantity-4'),
        'qty5': fields.integer('Quantity-5'),
    }
    _defaults = {
        'qty1': 1,
        'qty2': 5,
        'qty3': 10,
        'qty4': 0,
        'qty5': 0,
    }

    def print_report(self, cr, uid, ids, context=None):
        """
        To get the date and print the report
        @return : return report
        """
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, ['price_list','qty1', 'qty2','qty3','qty4','qty5'], context=context)
        res = res and res[0] or {}
        res['price_list'] = res['price_list'][0]
        datas['form'] = res
        return self.pool['report'].get_action(cr, uid, [], 'product.report_pricelist', data=datas, context=context)
