# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from report import report_sxw
from osv import osv
import pooler

from tools.translate import _

parents = {
    'tr':1,
    'li':1,
    'story': 0,
    'section': 0
}
class product_pricelist(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(product_pricelist, self).__init__(cr, uid, name, context)
        self.pricelist=False
        self.quantity=[]
        self.localcontext.update({
            'time': time,
            'get_pricelist': self._get_pricelist,
            'get_currency': self._get_currency,
            'get_categories': self._get_categories,
            'get_price': self._get_price,
            'get_quantity':self._get_quantity,
            'qty_header':self._qty_header,
        })
    def _qty_header(self,form):
        def _get_unit_text(obj, cr, uid, par_qty):
            if form[q]==1:
                return _('%d unit')%(par_qty)
            else:
                return _('%d units')%(par_qty)

        qty=[]
        self.pricelist=form['price_list']
        for i in range(1,6):
            q = 'qty%d'%i
            if form[q]:
                self.quantity.append(form[q])
                qty.append(_get_unit_text(self, self.cr, self.uid, form[q]))
        return qty


    def _get_quantity(self,form):
        qty=[]
        for i in range(1,6):
            q = 'qty%d'%i
            if form[q]:
                qty.append(form[q])
        return qty
    def _get_pricelist(self, pricelist_id):
        pool = pooler.get_pool(self.cr.dbname)
        pricelist = pool.get('product.pricelist').read(self.cr,self.uid,[pricelist_id],['name'])[0]
        return pricelist['name']
    def _get_currency(self, pricelist_id):
        pool = pooler.get_pool(self.cr.dbname)
        pricelist = pool.get('product.pricelist').read(self.cr,self.uid,[pricelist_id],['currency_id'])[0]
        return pricelist['currency_id'][1]
    def _get_categories(self, products):
        cat_ids=[]
        res=[]
        pool = pooler.get_pool(self.cr.dbname)
        pro_ids=[]
        for product in products:
            pro_ids.append(product.id)
            if product.categ_id.id not in cat_ids:
                cat_ids.append(product.categ_id.id)
        cats=pool.get('product.category').browse(self.cr,self.uid,cat_ids)
        for cat in cats:
            product_ids=pool.get('product.product').search(self.cr,self.uid,[('id','in',pro_ids),('categ_id','=',cat.id)])
            products = []
            for product in pool.get('product.product').browse(self.cr,self.uid,product_ids):
                val={
                         'id':product.id,
                         'name':product.name,
                         'code':product.code
                         }
                for qty in self.quantity:
                    val[str(qty)]=self._get_price(self.pricelist,product.id,qty)
                products.append(val)

            res.append({'name':cat.name,'products':products})
        return res

    def _get_price(self,pricelist_id, product_id,qty):
        pool = pooler.get_pool(self.cr.dbname)
        price_dict = pool.get('product.pricelist').price_get(self.cr,self.uid,[pricelist_id],product_id,qty)
        if price_dict[pricelist_id]:
            price = self.formatLang(price_dict[pricelist_id])
        else:
            res = pool.get('product.product').read(self.cr, self.uid,[product_id])
            price =  self.formatLang(res[0]['list_price'])
        return price

    def repeatIn(self, lst, name, nodes_parent=False,value=[],width=False,type=False):
        self._node.data = ''
        node = self._find_parent(self._node, nodes_parent or parents)
        ns = node.nextSibling
        if not lst:
            lst.append(1)
        for ns in node.childNodes :
            if ns and ns.nodeName!='#text' and ns.tagName=='blockTable' and len(value) :
                width_str = ns._attrs['colWidths'].nodeValue
                ns.removeAttribute('colWidths')
                if not width or width=='':
                    width=30
                if type.lower() in ('title'):
                    width=width*len(value)
                    width_str= '%d'%(float(width_str)+width)
                    ns.setAttribute('colWidths',width_str)
                else:
                    for v in value:
                        width_str +=',%d'%width

                    ns.setAttribute('colWidths',width_str)
                    child_list =  ns.childNodes
                    for child in child_list:
                        if child.nodeName=='tr':
                            lc = child.childNodes[1]
                            t=0
                            for v in value:
                                newnode = lc.cloneNode(1)
                                if type.lower() in ('string'):
                                    newnode.childNodes[1].lastChild.data="[[ %s['%s'] ]]"%(name,v)
                                elif type.lower() in ('label'):
                                    newnode.childNodes[1].lastChild.data= "%s"%(v)
                                child.appendChild(newnode)
                                newnode=False
        return super(product_pricelist,self).repeatIn(lst, name, nodes_parent=False)
#end
report_sxw.report_sxw('report.product.pricelist','product.product','addons/product/report/product_pricelist.rml',parser=product_pricelist)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

