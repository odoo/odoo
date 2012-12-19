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

import datetime
from openerp.report.interface import report_rml
from openerp.report.interface import toxml
from openerp import pooler
from openerp.osv import osv
import datetime

class report_custom(report_rml):

    def create_xml(self, cr, uid, ids, data, context):
        pool = pooler.get_pool(cr.dbname)

        price_list_id = data['form']['price_list']

        product_categ_id =pool.get('product.category').search(cr, uid, [])
        currency = pool.get('product.pricelist').read(cr, uid, [price_list_id], ['currency_id','name'])[0]


        qty =[]

        for i in range(1,6):
            q = 'qty%d'%i
            if data['form'][q]:
                qty.append(data['form'][q])

        if not qty:
            qty.append(1)

        product_xml = []
        cols = ''
        cols = cols+'6cm'
        title ='<title name=" Description " number="0" />'
        i=1
        for q in qty:
            cols = cols+',2.5cm'
            if q==1:
                title+='<title name="%d unit" number="%d"/>'%(q,i)
            else:
                title+='<title name="%d units" number="%d"/>'%(q,i)
            i+=1
        date = datetime.date.today()
        str_date=date.strftime("%d/%m/%Y")
        product_xml.append('<cols>'+cols+'</cols>')
        product_xml.append('<pricelist> %s </pricelist>'%currency['name'])
        product_xml.append('<currency> %s </currency>'%currency['currency_id'][1])
        product_xml.append('<date> %s </date>'%str_date)
        product_xml.append("<product>")

        for p_categ_id in product_categ_id:
            product_ids = pool.get('product.product').search(cr, uid, [('id','in',ids),('categ_id','=',p_categ_id)])
            if product_ids:
                categ_name = pool.get('product.category').read(cr, uid, [p_categ_id], ['name'])
                products = pool.get('product.product').read(cr, uid, product_ids, ['id','name','code'])
                pro = []
                i=0
                pro.append('<pro name="%s" categ="true">' % (categ_name[0]['name']))
                temp = []
                for q in qty:
                    temp.append('<price name=" " />')
                pro.extend(temp)
                pro.append('</pro>')
                for x in products:
                    #Replacement of special characters with their code html for allowing reporting - Edited by Hasa
                    x['name'] = x['name'].replace("&","&amp;")
                    x['name'] = x['name'].replace("\"","&quot;")
                    if x['code']:
                        pro.append('<pro name="[%s] %s" >' % (x['code'], x['name']))
                    else:
                        pro.append('<pro name="%s" >' % (x['name']))
                    temp = []
                    for q in qty:
                        price_dict = pool.get('product.pricelist').price_get(cr, uid, [price_list_id], x['id'], q, context=context)
                        if price_dict[price_list_id]:
                            price = price_dict[price_list_id]
                        else:
                            res = pool.get('product.product').read(cr, uid, [x['id']])
                            price =  res[0]['list_price']

                        temp.append('<price name="%.2f" />'%(price))
                    i+=1
                    pro.extend(temp)
                    pro.append('</pro>')
                product_xml.extend(pro)

        product_xml.append('</product>')

        xml = '''<?xml version="1.0" encoding="UTF-8" ?>
        <report>
        %s
        </report>
        '''  % (title+'\n'.join(product_xml))
        return self.post_process_xml_data(cr, uid, xml, context)

report_custom('report.pricelist.pricelist', 'product.product','','addons/product_pricelist_print/report/product_price.xsl')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

