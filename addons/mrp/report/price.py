# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import ir
import pooler
from report.interface import report_rml
from report.interface import toxml

from tools.translate import _


#FIXME: we should use toxml
class report_custom(report_rml):
    def create_xml(self, cr, uid, ids, datas, context={}):
        number = (datas.get('form', False) and datas['form']['number']) or 1

        def process_bom(bom, currency_id):
            xml = '<row>'
            sum = 0
            sum_strd = 0
            prod = pooler.get_pool(cr.dbname).get('product.product').browse(cr, uid, bom['product_id'])

            prod_name = bom['name']
            prod_qtty = bom['product_qty']
            prod_uom = prod.uom_id.name
            level = 1
            main_sp_price = ''
            main_sp_name = ''
            main_strd_price = ''
            main_strd_price = ''
            if prod.seller_ids and prod.seller_ids[0] :
                main_sp_name = '<b>' + prod.seller_ids[0].name.name + '</b>\r\n'
                pricelist_id = prod.seller_ids[0].name.property_product_pricelist_purchase.id
                if pricelist_id:
                    pricelist_obj = pooler.get_pool(cr.dbname).get('product.pricelist')
                    price = pricelist_obj.price_get(cr,uid,[pricelist_id], prod.id, number*prod_qtty or 1.0).setdefault(pricelist_id, 0)
                    price = pooler.get_pool(cr.dbname).get('res.currency').compute(cr, uid, pricelist_obj.browse(cr, uid, pricelist_id).currency_id.id, currency_id, price)
                else:
                    price = 0
                main_sp_price = '%.2f' % price + '\r\n'
                sum += prod_qtty*price

            main_strd_price = '%.2f' % prod.standard_price + '\r\n'
            sum_strd = prod_qtty*prod.standard_price

            sellers = ''
            sellers_price = ''
            for seller_id in prod.seller_ids:
                sellers +=  '- <i>'+ seller_id.name.name +'</i>\r\n'
                pricelist_id = seller_id.name.property_product_pricelist_purchase.id
                if pricelist_id:
                    pricelist_obj = pooler.get_pool(cr.dbname).get('product.pricelist')
                    price = pricelist_obj.price_get(cr,uid,[pricelist_id], prod.id, number*prod_qtty or 1.0).setdefault(pricelist_id, 0)
                    price = pooler.get_pool(cr.dbname).get('res.currency').compute(cr, uid, pricelist_obj.browse(cr, uid, pricelist_id).currency_id.id, currency_id, price)
                else:
                    price = 0
                sellers_price += '%.2f' % price + '\r\n'

            xml += "<col para='yes'>" + prod_name + '</col>'
            xml += "<col para='no'>" + main_sp_name +  sellers + '</col>'
            xml += "<col para='yes'>" + str(prod_qtty) + '</col>'
            xml += "<col para='yes'>" + prod_uom + '</col>'
            xml += "<col para='yes'>" + main_strd_price + '</col>'
            xml += "<col para='no'>" + main_sp_price +  sellers_price + '</col>'


            xml += '</row>'
            return xml, sum, sum_strd

        def process_workcenter(wrk):
            xml = '<row>'

            workcenter = pooler.get_pool(cr.dbname).get('mrp.workcenter').browse(cr, uid, wrk['workcenter_id'])

            xml += "<col para='yes'>" + wrk['name'] + '</col>'
            xml += "<col para='yes'>" +  '</col>'
            xml += "<col para='no'>" + '</col>'
            xml += "<col/>"
            xml += "<col para='no'>" + str(wrk['cycle']*workcenter.costs_cycle) + '</col>'
            xml += "<col para='yes'>" + str(wrk['hour']*workcenter.costs_hour) + '</col>'


            xml += '</row>'
            return xml, wrk['cycle']*workcenter.costs_cycle+wrk['hour']*workcenter.costs_hour


        xml = ''
        config_start = """
        <config>
            <date>09/09/2005</date>
            <PageSize>210.00mm,297.00mm</PageSize>
            <PageWidth>595.27</PageWidth>
            <PageHeight>841.88</PageHeight>
            <tableSize>60.00mm,60.00mm, 20.00mm, 20.00mm, 20.00mm, 20.00mm</tableSize>
            """
        config_stop = """
            <report-footer>Generated by Open ERP</report-footer>
        </config>
        """
        header = """
            <header>
            <field>%s</field>
            <field>%s</field>
            <field>%s</field>
            <field>%s</field>
            <field>%s</field>
            <field>%s</field>
            </header>
            """ % (_('Product name'), _('Product supplier'), _('Product quantity'), _('Product uom'), _('Product Standard Price'), _('Unit Product Price'))
        workcenter_header = """
            <lines style='header'>
                <row>
                    <col>%s</col>
                    <col/>
                    <col/>
                    <col/>
                    <col>%s</col>
                    <col>%s</col>
                </row>
            </lines>
        """ % (_('Workcenter name'), _('Cycles Cost'), _('Total hourly costs'))
        prod_header = """
            <lines style='header'>
                <row>
                    <col para='yes'>%s</col>
                    <col para='yes'>%s</col>
                    <col para='yes'>%s</col>
                    <col para='yes'>%s</col>
                    <col para='yes'>%s</col>
                    <col para='yes'>%s</col>
                </row>
            </lines>
        """ % (_('Product name'), _('Product supplier'), _('Product Quantity'), _('Product uom'), _('Product Standard Price'), _('Unit Product Price'))

        company_currency = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid).company_id.currency_id.id
        first = True
        for prod_id in ids:
            bom_ids = pooler.get_pool(cr.dbname).get('mrp.bom').search(cr, uid, [('product_id','=',prod_id)])
            prod = pooler.get_pool(cr.dbname).get('product.product').browse(cr, uid, prod_id)

            for bom_id in bom_ids:
                bom = pooler.get_pool(cr.dbname).get('mrp.bom').browse(cr, uid, bom_id)

                sub_boms = pooler.get_pool(cr.dbname).get('mrp.bom')._bom_explode(cr, uid, bom, number, [])
                total = 0
                total_strd = 0
                parent_bom = {'product_qty': bom.product_qty, 'name': bom.product_id.name, 'product_uom': bom.product_id.uom_id.factor, 'product_id': bom.product_id.id}
                xml_tmp = ''
                for sub_bom in (sub_boms and sub_boms[0]) or [parent_bom]:
                    txt, sum, sum_strd = process_bom(sub_bom, company_currency)
                    xml_tmp +=  txt
                    total += sum
                    total_strd += sum_strd
                if not first:
                    xml += prod_header
                xml += "<lines style='lines'>" + xml_tmp + '</lines>'
                xml += "<lines style='sub_total'><row><col>%s : </col><col>(" % (_('SUBTOTAL')) + str(number) + " %s)</col><col/><col/><col>" % (_('products')) + '%.2f' % total_strd + '</col><col>' + '%.2f' % total  + '</col></row></lines>'
                total2 = 0
                xml_tmp = ''
                for wrk in (sub_boms and sub_boms[1]):
                    txt, sum = process_workcenter(wrk)
                    xml_tmp += txt
                    total2 += sum
                if xml_tmp:
                    xml += workcenter_header
                    xml += "<lines style='lines'>" + xml_tmp + '</lines>'
                    xml += "<lines style='sub_total'><row><col>%s : </col><col>(" % (_('SUBTOTAL')) + str(number) + " %s)</col><col/><col/><col/><col>" % (_('products')) + '%.2f' % total2 + '</col></row></lines>'
                xml += "<lines style='total'><row><col>%s : </col><col>(" % (_('TOTAL')) + str(number) + " %s)</col><col/><col/><col>" % (_('products')) + '%.2f' % (total_strd+total2) + "</col><col>" + '%.2f' % (total+total2) + '</col></row></lines>'

                first = False

        xml = '<?xml version="1.0" ?><report>' + config_start + '<report-header>%s\n\r' % (_('Product Cost Structure')) + prod.name  + '</report-header>'+ config_stop +  header + xml + '</report>'

        return xml

report_custom('report.product.price', 'product.product', '', 'addons/mrp/report/price.xsl')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

