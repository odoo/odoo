# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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
##############################################################################

from report.interface import report_rml
from report.interface import toxml
import pooler


class report_custom(report_rml):

    def create_xml(self, cr, uid, ids, datas, context=None):
        pool = pooler.get_pool(cr.dbname)
        product_obj = pool.get('product.product')
        location_obj = pool.get('stock.location')

        products = product_obj.read(cr, uid, ids, ['name','uom_id'])
        cr.execute('SELECT id FROM stock_location WHERE usage = %s',
                ('internal',))
        location_ids = [ x[0] for x in cr.fetchall() ]
        location_ids.sort()
        locs_info = {}
        locs_name = dict(location_obj.name_get(cr, uid, location_ids))
        for location_id in locs_name.keys():
            locs_info[location_id] = location_obj._product_get(cr, uid,
                    location_id, ids)

        xml = '<?xml version="1.0" ?><report>'
        for p in products:
            xml += '<product>' \
                '<name>' + toxml(p['name']) + '</name>' \
                '<unit>' + toxml(p['uom_id'][1]) + '</unit>' \
                '<locations>'
            for loc_id in locs_info.keys():
                if locs_info[loc_id].get(p['id']):
                    xml += '<location>'
                    xml += '<loc_name>' + toxml(locs_name[loc_id]) \
                            + '</loc_name>'
                    xml += '<loc_qty>' + toxml(locs_info[loc_id].get(p['id'])) \
                            + '</loc_qty>'
                    xml += '</location>'
            xml += '</locations>' \
                '</product>'
        xml += '</report>'
        return self.post_process_xml_data(cr, uid, xml, context)

report_custom('report.stock.product.location', 'stock.location', '',
        'addons/stock/report/product_location.xsl')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

