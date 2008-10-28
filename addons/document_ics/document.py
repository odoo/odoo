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

from osv import osv, fields
from osv.orm import except_orm
import os
import StringIO
import base64
import datetime
import time

ICS_TAGS = {
    'summary':'normal',
    'uid':'normal' ,
    'dtstart':'date' ,
    'dtend':'date' ,
    'created':'date' ,
    'dt-stamp':'date' ,
    'last-modified':'normal' ,
    'url':'normal' ,
    'attendee':'multiple',
    'location':'normal',
    'categories': 'normal',
    'description':'normal'
}

class document_directory_ics_fields(osv.osv):
    _name = 'document.directory.ics.fields'
    _columns = {
        'field_id': fields.many2one('ir.model.fields', 'Open ERP Field', required=True),
        'name': fields.selection(map(lambda x: (x,x), ICS_TAGS.keys()),'ICS Value', required=True),
        'content_id': fields.many2one('document.directory.content', 'Content', required=True, ondelete='cascade')
    }
document_directory_ics_fields()

class document_directory_content(osv.osv):
    _inherit = 'document.directory.content'
    _columns = {
        'ics_object_id': fields.many2one('ir.model', 'Object'),
        'ics_domain': fields.char('Domain', size=64),
        'ics_field_ids': fields.one2many('document.directory.ics.fields', 'content_id', 'Fields Mapping')
    }
    _defaults = {
        'ics_domain': lambda *args: '[]'
    }
    def process_read_ics(self, cr, uid, node, context={}):
        print 'READ ICS'
        import vobject
        obj_class = self.pool.get(node.content.ics_object_id.model)
        # Can be improved to use context and active_id !
        domain = eval(node.content.ics_domain)
        ids = obj_class.search(cr, uid, domain, context)
        cal = vobject.iCalendar()
        for obj in obj_class.browse(cr, uid, ids, context):
            event = cal.add('vevent')
            for field in node.content.ics_field_ids:
                if ICS_TAGS[field.name]=='normal':
                    value = getattr(obj, field.field_id.name) or ''
                    event.add(field.name).value = value
                elif ICS_TAGS[field.name]=='date':
                    dt = getattr(obj, field.field_id.name) or time.strftime('%Y-%m-%d %H:%M:%S')
                    if len(dt)==10:
                        if field.name=='dtend':
                            dt = dt+' 10:00:00'
                        else:
                            dt = dt+' 09:00:00'
                    value = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                    event.add(field.name).value = value
        s= StringIO.StringIO(cal.serialize())
        s.name = node
        return s
document_directory_content()

