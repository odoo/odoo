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

from report.interface import report_rml
import pooler
from xml.dom import minidom
import re
import base64
import photo_shadow
import addons

def _to_unicode(s):
    try:
        return s.decode('utf-8')
    except UnicodeError:
        try:
            return s.decode('latin')
        except UnicodeError:
            try:
                return s.encode('ascii')
            except UnicodeError:
                return s

def _to_decode(s):
    try:
        return s.encode('utf-8')
    except UnicodeError:
        try:
            return s.encode('latin')
        except UnicodeError:
            try:
                return s.decode('ascii')
            except UnicodeError:
                return s


class auction_catalog(report_rml):

    def create_xml(self, cr, uid, ids, data, context):
        xml = self.catalog_xml(cr, uid, ids, data, context)
        temp = self.post_process_xml_data(cr, uid, xml, context)

        return temp
    def catalog_xml(self, cr, uid, ids, data, context, cwid="0"):
        impl = minidom.getDOMImplementation()
        doc = impl.createDocument(None, "report", None)
        catalog=doc.createElement('catalog')
        doc.documentElement.appendChild(catalog)

        auction_lot_pool = pooler.get_pool(cr.dbname).get('auction.lots')
        auction_dates_pool = pooler.get_pool(cr.dbname).get('auction.dates')
        for auction in auction_dates_pool.browse(cr, uid, ids, context=context):
            auction_lot_ids = auction_lot_pool.search(cr, uid, [('auction_id', '=', auction.id)])
            key = 'name'
            categ = doc.createElement(key)
            categ.appendChild(doc.createTextNode(_to_decode(auction.name)))
            catalog.appendChild(categ)

            #Auctuion Date element
            categ = doc.createElement("AuctionDate1")
            categ.appendChild(doc.createTextNode(_to_decode(auction.auction1)))
            catalog.appendChild(categ)

            # Action Date 2 element
            categ = doc.createElement("AuctionDate2")
            categ.appendChild(doc.createTextNode(_to_decode(auction.auction2)))
            catalog.appendChild(categ)

            # promotion element
            promo = doc.createElement('promotion1')
            fp = file(addons.get_module_resource('auction','report', 'images', 'flagey_logo.jpg'),'r')
            file_data = fp.read()
            promo.appendChild(doc.createTextNode(base64.encodestring(file_data)))
            catalog.appendChild(promo)
            promo = doc.createElement('promotion2')
            fp = file(addons.get_module_resource('auction','report', 'images', 'flagey_logo.jpg'),'r')
            file_data = fp.read()
            promo.appendChild(doc.createTextNode(base64.encodestring(file_data)))
            catalog.appendChild(promo)

            #product element
            products = doc.createElement('products')
            catalog.appendChild(products)
            side = 0
            length = 0
            for cat in auction_lot_pool.browse(cr, uid, auction_lot_ids, context=context):
                product = doc.createElement('product')
                products.appendChild(product)
                if cat.obj_desc:
                    infos = doc.createElement('infos')
                    lines = re.split('<br/>|\n', _to_unicode(cat.obj_desc))
                    for line in lines:
                        xline = doc.createElement('info')
                        xline.appendChild(doc.createTextNode(_to_decode(line)))
                        infos.appendChild(xline)
                    product.appendChild(infos)
                    if cat.lot_num:
                        lnum = doc.createElement('lot_num')
                        lnum.appendChild(doc.createTextNode(_to_decode(str(cat.lot_num))))
                        infos.appendChild(lnum)

                    if cat.image:
                        import tempfile
                        limg = doc.createElement('photo_small')

                        file_name = tempfile.mktemp(prefix='openerp_auction_', suffix='.jpg')
                        fp = file(file_name, 'w')
                        content = base64.decodestring(cat.image)
                        fp.write(content)
                        fp.close()
                        fp = file(file_name,'r')
                        test_file_name = tempfile.mktemp(prefix='openerp_auction_test_', suffix='.jpg')
                        size = photo_shadow.convert_catalog(fp, test_file_name,110)
                        fp = file(test_file_name)
                        file_data = fp.read()
                        test_data = base64.encodestring(file_data)
                        fp.close()
                        limg.appendChild(doc.createTextNode(test_data))
                        infos.appendChild(limg)

                if cat.lot_est1:
                    ref2 = doc.createElement(key)
                    ref2.appendChild(doc.createTextNode( _to_decode(str(cat.lot_est1 or 0.0))))
                    product.appendChild(ref2)
                if cat.lot_est2:
                    ref2 = doc.createElement(key)
                    ref2.appendChild(doc.createTextNode( _to_decode(str(cat.lot_est2 or 0.0))))
                    product.appendChild(ref2)

                oldlength = length
                length += 2.0
                if length>23.7:
                    side += 1
                    length = length - oldlength
                    ref3 = doc.createElement('newpage')
                    ref3.appendChild(doc.createTextNode( "1" ))
                    product.appendChild(ref3)
                if side%2:
                    ref4 = doc.createElement('side')
                    ref4.appendChild(doc.createTextNode( "1" ))
                    product.appendChild(ref4)
        xml1 = doc.toxml()
        return xml1
auction_catalog('report.auction.cat_flagy', 'auction.dates','','addons/auction/report/catalog2.xsl')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

