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

import time

from openerp import pooler
from openerp.osv import osv
from openerp.report import report_sxw
from openerp.tools.translate import _

class product_pricelist(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(product_pricelist, self).__init__(cr, uid, name, context=context)
        self.pricelist=False
        self.quantity=[]
        self.localcontext.update({
            'time': time,
            'get_pricelist': self._get_pricelist,
            'get_currency': self._get_currency,
            'get_currency_symbol': self._get_currency_symbol,  # TODO 7.0 - remove this - unused
            'get_categories': self._get_categories,
            'get_price': self._get_price,
            'get_titles': self._get_titles,
        })

    def _get_titles(self, form):
        lst = []
        vals = {}
        qtys = 1

        for i in range(1,6):
            if form['qty'+str(i)]!=0:
                vals['qty'+str(qtys)] = str(form['qty'+str(i)]) + ' units'
            qtys += 1
        lst.append(vals)
        return lst

    def _set_quantity(self, form):
        for i in range(1,6):
            q = 'qty%d'%i
            if form[q] >0 and form[q] not in self.quantity:
                self.quantity.append(form[q])
            else:
                self.quantity.append(0)
        return True

    def _get_pricelist(self, pricelist_id):
        pool = pooler.get_pool(self.cr.dbname)
        pricelist = pool.get('product.pricelist').read(self.cr, self.uid, [pricelist_id], ['name'], context=self.localcontext)[0]
        return pricelist['name']

    def _get_currency(self, pricelist_id):
        pool = pooler.get_pool(self.cr.dbname)
        pricelist = pool.get('product.pricelist').read(self.cr, self.uid, [pricelist_id], ['currency_id'], context=self.localcontext)[0]
        return pricelist['currency_id'][1]

    # TODO 7.0 - remove this method, its unused
    def _get_currency_symbol(self, pricelist_id):
        pool = pooler.get_pool(self.cr.dbname)
        pricelist = pool.get('product.pricelist').read(self.cr, self.uid, [pricelist_id], ['currency_id'], context=self.localcontext)[0]
        symbol = pool.get('res.currency').read(self.cr, self.uid, [pricelist['currency_id'][0]], ['symbol'], context=self.localcontext)[0]
        return symbol['symbol'] or ''

    def _get_categories(self, products, form):
        cat_ids=[]
        res=[]
        self.pricelist = form['price_list']
        self._set_quantity(form)
        pool = pooler.get_pool(self.cr.dbname)
        pro_ids=[]
        for product in products:
            pro_ids.append(product.id)
            if product.categ_id.id not in cat_ids:
                cat_ids.append(product.categ_id.id)

        cats = pool.get('product.category').name_get(self.cr, self.uid, cat_ids, context=self.localcontext)
        if not cats:
            return res
        for cat in cats:
            product_ids=pool.get('product.product').search(self.cr, self.uid, [('id', 'in', pro_ids), ('categ_id', '=', cat[0])], context=self.localcontext)
            products = []
            for product in pool.get('product.product').read(self.cr, self.uid, product_ids, ['name', 'code'], context=self.localcontext):
                val = {
                     'id':product['id'],
                     'name':product['name'],
                     'code':product['code']
                }
                i = 1
                for qty in self.quantity:
                    if qty == 0:
                        val['qty'+str(i)] = 0.0
                    else:
                        val['qty'+str(i)]=self._get_price(self.pricelist, product['id'], qty)
                    i += 1
                products.append(val)
            res.append({'name':cat[1],'products': products})
        return res

    def _get_price(self, pricelist_id, product_id, qty):
        sale_price_digits = self.get_digits(dp='Product Price')
        pool = pooler.get_pool(self.cr.dbname)
        pricelist = self.pool.get('product.pricelist').browse(self.cr, self.uid, [pricelist_id], context=self.localcontext)[0]
        price_dict = pool.get('product.pricelist').price_get(self.cr, self.uid, [pricelist_id], product_id, qty, context=self.localcontext)
        if price_dict[pricelist_id]:
            price = self.formatLang(price_dict[pricelist_id], digits=sale_price_digits, currency_obj=pricelist.currency_id)
        else:
            res = pool.get('product.product').read(self.cr, self.uid, [product_id])
            price =  self.formatLang(res[0]['list_price'], digits=sale_price_digits, currency_obj=pricelist.currency_id)
        return price

report_sxw.report_sxw('report.product.pricelist','product.product','addons/product/report/product_pricelist.rml',parser=product_pricelist)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
