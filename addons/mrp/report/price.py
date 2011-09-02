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

import pooler
from report.interface import report_rml
#from report.interface import toxml
from tools import to_xml
from report import report_sxw
from datetime import datetime
from tools.translate import _
import tools

#FIXME: we should use toxml
class report_custom(report_rml):
    def create_xml(self, cr, uid, ids, datas, context=None):
        number = (datas.get('form', False) and datas['form']['number']) or 1
        pool = pooler.get_pool(cr.dbname)
        product_pool = pool.get('product.product')
        product_uom_pool = pool.get('product.uom')
        supplier_info_pool = pool.get('product.supplierinfo')
        workcenter_pool = pool.get('mrp.workcenter')
        user_pool = pool.get('res.users')
        bom_pool = pool.get('mrp.bom')
        rml_obj=report_sxw.rml_parse(cr, uid, product_pool._name,context)
        rml_obj.localcontext.update({'lang':context.get('lang',False)})
        company_currency = user_pool.browse(cr, uid, uid).company_id.currency_id
        def process_bom(bom, currency_id, factor=1):
            xml = '<row>'
            sum = 0
            sum_strd = 0
            prod = product_pool.browse(cr, uid, bom['product_id'])

            prod_name = to_xml(tools.ustr(bom['name']))
            prod_qtty = factor * bom['product_qty']
            product_uom = product_uom_pool.browse(cr, uid, bom['product_uom'], context=context)
            main_sp_price, main_sp_name , main_strd_price = '','',''
            sellers, sellers_price = '',''

            if prod.seller_id:
                main_sp_name = "<b>%s</b>\r\n" % to_xml(tools.ustr(prod.seller_id.name))
                price = supplier_info_pool.price_get(cr, uid, prod.seller_id.id, prod.id, number*prod_qtty)[prod.seller_id.id]
                price = product_uom_pool._compute_price(cr, uid, prod.uom_id.id, price, to_uom_id=product_uom.id)
                main_sp_price = """<b>"""+rml_obj.formatLang(price)+' '+ company_currency.symbol+"""</b>\r\n"""
                sum += prod_qtty*price
            std_price = product_uom_pool._compute_price(cr, uid, prod.uom_id.id, prod.standard_price, to_uom_id=product_uom.id)
            main_strd_price = str(std_price) + '\r\n'
            sum_strd = prod_qtty*std_price
            for seller_id in prod.seller_ids:
                sellers +=  '- <i>'+ to_xml(tools.ustr(seller_id.name.name)) +'</i>\r\n'
                price = supplier_info_pool.price_get(cr, uid, seller_id.name.id, prod.id, number*prod_qtty)[seller_id.name.id]
                price = product_uom_pool._compute_price(cr, uid, prod.uom_id.id, price, to_uom_id=product_uom.id)
                sellers_price += """<i>"""+rml_obj.formatLang(price) +' '+ company_currency.symbol +"""</i>\r\n"""
            xml += """<col para='yes'> """+ to_xml(tools.ustr(prod_name)) +""" </col>
                    <col para='yes'> """+ to_xml(tools.ustr(main_sp_name)) + to_xml(tools.ustr(sellers)) + """ </col>
                    <col f='yes'>"""+ rml_obj.formatLang(prod_qtty) +' '+ product_uom.name +"""</col>
                    <col f='yes'>"""+ rml_obj.formatLang(float(main_strd_price)) +' '+ company_currency.symbol +"""</col>
                    <col f='yes'>""" + main_sp_price + sellers_price + """</col>'"""

            xml += '</row>'
            return xml, sum, sum_strd

        def process_workcenter(wrk):
            workcenter = workcenter_pool.browse(cr, uid, wrk['workcenter_id'])
            cost_cycle = wrk['cycle']*workcenter.costs_cycle
            cost_hour = wrk['hour']*workcenter.costs_hour
            total = cost_cycle + cost_hour
            xml = '<row>'
            xml += "<col para='yes'>" + workcenter.name + '</col>'
            xml += "<col/>"
            xml += """<col f='yes'>"""+rml_obj.formatLang(cost_cycle)+' '+ company_currency.symbol + """</col>"""
            xml += """<col f='yes'>"""+rml_obj.formatLang(cost_hour)+' '+ company_currency.symbol + """</col>"""
            xml += """<col f='yes'>"""+rml_obj.formatLang(cost_hour + cost_cycle)+' '+ company_currency.symbol + """</col>"""
            xml += '</row>'

            return xml, total


        xml = ''
        config_start = """
        <config>
            <date>""" + to_xml(rml_obj.formatLang(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),date_time=True)) + """</date>
            <company>%s</company>
            <PageSize>210.00mm,297.00mm</PageSize>
            <PageWidth>595.27</PageWidth>
            <PageHeight>841.88</PageHeight>
            <tableSize>55.00mm,58.00mm,29.00mm,29.00mm,29.00mm</tableSize>
            """ % (user_pool.browse(cr, uid, uid).company_id.name)
        config_stop = """
            <report-footer>Generated by OpenERP</report-footer>
        </config>
        """

        workcenter_header = """
            <lines style='header'>
                <row>
                    <col>%s</col>
                    <col t='yes'/>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                </row>
            </lines>
        """ % (_('Work Center name'), _('Cycles Cost'), _('Hourly Cost'),_('Work Cost'))
        prod_header = """
                <row>
                    <col>%s</col>
                    <col>%s</col>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                </row>
        """ % (_('Components'), _('Components suppliers'), _('Quantity'),_('Cost Price per Uom'), _('Supplier Price per Uom'))

        purchase_price_digits = rml_obj.get_digits(dp='Purchase Price')

        for product in product_pool.browse(cr, uid, ids, context=context):
            bom_id = bom_pool._bom_find(cr, uid, product.id, product.uom_id.id)
            title = "<title>%s</title>" %(_("Cost Structure"))
            title += "<title>%s</title>" % (to_xml(tools.ustr(product.name))).replace('&', '&amp;')
            xml += "<lines style='header'>" + title + prod_header + "</lines>"
            if not bom_id:
                total_strd = number * product.standard_price
                total = number * product_pool.price_get(cr, uid, [product.id], 'standard_price')[product.id]
                xml += """<lines style='lines'><row>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    </row></lines>"""
                xml += """<lines style='total'> <row>
                    <col> """ + _('Total Cost of %s %s') % (str(number), product.uom_id.name) + """: </col>
                    <col/>
                    <col f='yes'/>
                    <col t='yes'>"""+ rml_obj.formatLang(total_strd, digits=purchase_price_digits) +' '+ company_currency.symbol + """</col>
                    <col t='yes'>"""+ rml_obj.formatLang(total, digits=purchase_price_digits) +' '+ company_currency.symbol + """</col>
                    </row></lines>'"""
            else:
                bom = bom_pool.browse(cr, uid, bom_id, context=context)
                factor = number * product.uom_id.factor / bom.product_uom.factor
                sub_boms = bom_pool._bom_explode(cr, uid, bom, factor / bom.product_qty)
                total = 0
                total_strd = 0
                parent_bom = {
                        'product_qty': bom.product_qty,
                        'name': bom.product_id.name,
                        'product_uom': bom.product_uom.id,
                        'product_id': bom.product_id.id
                }
                xml_tmp = ''
                for sub_bom in (sub_boms and sub_boms[0]) or [parent_bom]:
                    txt, sum, sum_strd = process_bom(sub_bom, company_currency.id)
                    xml_tmp +=  txt
                    total += sum
                    total_strd += sum_strd

                xml += "<lines style='lines'>" + xml_tmp + '</lines>'
                xml += """<lines style='sub_total'> <row>
                    <col> """ + _('Components Cost of %s %s') % (str(number), product.uom_id.name) + """: </col>
                    <col/>
                    <col t='yes'/>
                    <col t='yes'>"""+ rml_obj.formatLang(total_strd, digits=purchase_price_digits) +' '+ company_currency.symbol + """</col>
                    <col t='yes'></col>
                    </row></lines>'"""

                total2 = 0
                xml_tmp = ''
                for wrk in (sub_boms and sub_boms[1]):
                    txt, sum = process_workcenter(wrk)
                    xml_tmp += txt
                    total2 += sum
                if xml_tmp:
                    xml += workcenter_header
                    xml += "<lines style='lines'>" + xml_tmp + '</lines>'
                    xml += """<lines style='sub_total'> <row>
                    <col> """ + _('Work Cost of %s %s') % (str(number), product.uom_id.name) +""": </col>
                    <col/>
                    <col/>
                    <col/>
                    <col t='yes'>"""+ rml_obj.formatLang(total2, digits=purchase_price_digits) +' '+ company_currency.symbol +"""</col>
                    </row></lines>'"""
                xml += """<lines style='total'> <row>
                    <col> """ + _('Total Cost of %s %s') % (str(number), product.uom_id.name) + """: </col>
                    <col/>
                    <col t='yes'/>
                    <col t='yes'>"""+ rml_obj.formatLang(total_strd+total2, digits=purchase_price_digits) +' '+ company_currency.symbol + """</col>
                    <col t='yes'></col>
                    </row></lines>'"""

        xml = '<?xml version="1.0" ?><report>' + config_start + config_stop + xml + '</report>'

        return xml

report_custom('report.product.price', 'product.product', '', 'addons/mrp/report/price.xsl')
