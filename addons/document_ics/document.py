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

from osv import osv, fields
from osv.orm import except_orm
import os
import StringIO
import base64
import datetime
import time
import random

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
    'description':'normal',

    # TODO: handle the 'duration' property
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
    def process_write_ics(self, cr, uid, node, data, context={}):
        import vobject
        parsedCal = vobject.readOne(data)
        fields = {}
        fobj = self.pool.get('document.directory.content')
        content = fobj.browse(cr, uid, node.content.id, context)

        idomain = {}
        for d in eval(content.ics_domain):
            idomain[d[0]]=d[2]
        for n in content.ics_field_ids:
            fields[n.name] = n.field_id.name
        if 'uid' not in fields:
            return True
        for child in parsedCal.getChildren():
            result = {}
            uuid = None
            for event in child.getChildren():
                if event.name.lower()=='uid':
                    uuid = event.value
                if event.name.lower() in fields:
                    if ICS_TAGS[event.name.lower()]=='normal':
                        result[fields[event.name.lower()]] = event.value.encode('utf8')
                    elif ICS_TAGS[event.name.lower()]=='date':
                        result[fields[event.name.lower()]] = event.value.strftime('%Y-%m-%d %H:%M:%S')
            if not uuid:
                continue

            fobj = self.pool.get(content.ics_object_id.model)
            id = fobj.search(cr, uid, [(fields['uid'], '=', uuid.encode('utf8'))], context=context)
            if id:
                fobj.write(cr, uid, id, result, context=context)
            else:
                r = idomain.copy()
                r.update(result)
                fobj.create(cr, uid, r, context=context)

        return True

    def process_read_ics(self, cr, uid, node, context={}):
        import vobject
        obj_class = self.pool.get(node.content.ics_object_id.model)
        # Can be improved to use context and active_id !
        domain = eval(node.content.ics_domain)
        ids = obj_class.search(cr, uid, domain, context)
        cal = vobject.iCalendar()
        for obj in obj_class.browse(cr, uid, ids, context):
            event = cal.add('vevent')
            for field in node.content.ics_field_ids:
                value = getattr(obj, field.field_id.name)
                if (not value) and field.name=='uid':
                    value = 'OpenERP-'+str(random.randint(1999999999, 9999999999))
                    obj_class.write(cr, uid, [obj.id], {field.field_id.name: value})
                if ICS_TAGS[field.name]=='normal':
                    if type(value)==type(obj):
                        value=value.name
                    value = value or ''
                    event.add(field.name).value = value or ''
                elif ICS_TAGS[field.name]=='date':
                    dt = value or time.strftime('%Y-%m-%d %H:%M:%S')
                    if len(dt)==10:
                        dt = dt+' 09:00:00'
                    value = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                    event.add(field.name).value = value
        s= StringIO.StringIO(cal.serialize().encode('utf8'))
        s.name = node
        cr.commit()
        return s
document_directory_content()

class crm_case(osv.osv):
    _inherit = 'crm.case'
    _columns = {
        'code': fields.char('Calendar Code', size=64)
    }
crm_case()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

