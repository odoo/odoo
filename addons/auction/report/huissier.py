# -*- encoding: utf-8 -*-
# -*-encoding: iso8859-1 -*-
##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
####################################### i#######################################

import pooler
from osv.osv import osv, orm
from report.interface import report_rml
#FIXME: use the one from tools and delete the one from report
from report.int_to_text import int_to_text

def toxml(val):
    return val.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;').decode('utf-8').encode('latin1', 'replace')

class report_custom(report_rml):
    def __init__(self, name, table, tmpl, xsl):
        report_rml.__init__(self, name, table, tmpl, xsl)

    def create_xml(self,cr, uid, ids, datas, context={}):
        pool= pooler.get_pool(cr.dbname)
        lots = pool.get('auction.lots').browse(cr, uid, ids)
        auction = lots[0].auction_id

        xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<report>
    <auction>
        <name>%s</name>
        <date-au1>%s</date-au1>
    </auction>''' % (toxml(auction['name']), toxml(auction['auction1']))
    
        i = 0
        for l in lots:
#           l['id_cont'] = str(i)
            if l['obj_price']==0:
                price_french = 'retiré'
            else:
                price_french = int_to_text(int(l['obj_price'] or 0.0))+' eur'
            i+=1
            xml += '''  <object>
        <number>%d</number>
        <obj_num>%d</obj_num>
        <lot_desc>%s</lot_desc>
        <price>%s</price>
        <obj_price>%s</obj_price>
    </object>''' % (i, l['obj_num'], toxml(l['name']), price_french, str(l['obj_price'] or '/'))
        xml += '</report>'
        
#       file('/tmp/terp.xml','wb+').write(xml)
        return xml

report_custom('report.flagey.huissier', 'auction.lots', '', 'addons/auction/report/huissier.xsl')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

