# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com) 
# All Right Reserved
#
# Authors : Nicolas Bessi (Camptocamp)
#           Yannick Vaucher (Camptocamp)
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

from openerp import pooler

class WebKitHelper(object):
    """Set of usefull report helper"""
    def __init__(self, cursor, uid, report_id, context):
        "constructor"
        self.cursor = cursor
        self.uid = uid
        self.pool = pooler.get_pool(self.cursor.dbname)
        self.report_id = report_id

    def embed_image(self, type, img, width=0, height=0, unit="px"):
        "Transform a DB image into an embedded HTML image"

        if width :
            width = 'width: %s%s;'%(width, unit)
        else :
            width = ' '
        if height :
            height = 'height: %s%s;'%(height, unit)
        else :
            height = ' '
        toreturn = '<img style="%s%s" src="data:image/%s;base64,%s" />'%(
            width,
            height,
            type, 
            str(img))
        return toreturn
            
            
    def get_logo_by_name(self, name, company_id=None):
        """Return logo by name"""
        header_obj = self.pool.get('ir.header_img')
        domain = [('name','=',name)]
        if company_id:
            domain.append(('company_id', '=', company_id))
        header_img_id = header_obj.search(self.cursor, 
                                          self.uid, 
                                          domain)
        if not header_img_id :
            return u''
        if isinstance(header_img_id, list):
            header_img_id = header_img_id[0]

        head = header_obj.browse(self.cursor, self.uid, header_img_id)
        return (head.img, head.type)
            
    def embed_logo_by_name(self, name, width=0, height=0, unit="px", company_id=None):
        """Return HTML embedded logo by name"""
        img, type = self.get_logo_by_name(name, company_id=company_id)
        return self.embed_image(type, img, width, height, unit)
        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
