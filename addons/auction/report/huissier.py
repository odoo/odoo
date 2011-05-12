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
#FIXME: use the one from tools and delete the one from report
from report.int_to_text import int_to_text
from tools import to_xml as toxml
from tools import ustr

class report_custom(report_rml):
    def __init__(self, name, table, tmpl, xsl):
        report_rml.__init__(self, name, table, tmpl, xsl)

    def create_xml(self,cr, uid, ids, datas, context=None):
        pool= pooler.get_pool(cr.dbname)
        lots = pool.get('auction.lots').browse(cr, uid, ids, context=context)
        auction = lots[0].auction_id

        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<report>
    <auction>
        <name>%s</name>
        <date-au1>%s</date-au1>
    </auction>''' % (toxml(auction['name']), toxml(auction['auction1']))

        i = 0
        for l in lots:
            if l['obj_price']==0:
                price_french = u'retiré'
            else:
                price_french = int_to_text(int(l['obj_price'] or 0.0))+' eur'
            i+=1
            xml += '''  <object>
        <number>%d</number>
        <obj_num>%d</obj_num>
        <lot_desc>%s</lot_desc>
        <price>%s</price>
        <obj_price>%s</obj_price>
    </object>''' % (i, l['obj_num'], ustr(toxml(l['name'])), ustr(price_french), ustr(l['obj_price'] or '/'))
        xml += '</report>'

        return xml

report_custom('report.flagey.huissier', 'auction.lots', '', 'addons/auction/report/huissier.xsl')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

