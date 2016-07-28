# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from odoo import api

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

    @api.multi
    def print_report(self):
        """
        To get the date and print the report
        @return : return report
        """
        datas = {'ids': self.env.context.get('active_ids', [])}
        res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = res and res[0] or {}
        res['price_list'] = res['price_list'][0]
        datas['form'] = res
        return self.env['report'].get_action([], 'product.report_pricelist', data=datas)
