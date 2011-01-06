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
import tools
from tools.translate import _
import mx

ICS_TAGS = {
    'summary':'normal',
    'uid':'normal' ,
    'dtstart':'date' ,
    'dtend':'date' ,
    'created':'date' ,
    'dtstamp':'date' ,
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
        'name': fields.selection(map(lambda x: (x, x), ICS_TAGS.keys()), 'ICS Value', required=True),
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
        def ics_datetime(idate, short=False):
            if short:
                return datetime.date.fromtimestamp(time.mktime(time.strptime(idate, '%Y-%m-%d')))
            else:
                return mx.DateTime.strptime(idate, '%Y-%m-%d %H:%M:%S')

        import vobject
        obj_class = self.pool.get(node.content.ics_object_id.model)
        # Can be improved to use context and active_id !
        domain = eval(node.content.ics_domain)
        ids = obj_class.search(cr, uid, domain, context)
        cal = vobject.iCalendar()
        for obj in obj_class.browse(cr, uid, ids, context):
            event = cal.add('vevent')
            # Fix dtstamp et last-modified with create and write date on the object line
            perm = obj_class.perm_read(cr, uid, [obj.id], context)
            event.add('created').value = ics_datetime(time.strftime('%Y-%m-%d %H:%M:%S'))
            event.add('dtstamp').value = ics_datetime(perm[0]['create_date'][:19])
            if perm[0]['write_date']:
                event.add('last-modified').value = ics_datetime(perm[0]['write_date'][:19])
            for field in node.content.ics_field_ids:
                value = getattr(obj, field.field_id.name)
                value = value and tools.ustr(value)
                if (not value) and field.name=='uid':
                    value = 'OpenERP-%s_%s@%s' % (node.content.ics_object_id.model, str(obj.id), cr.dbname,)
                    obj_class.write(cr, uid, [obj.id], {field.field_id.name: value})
                if ICS_TAGS[field.name]=='normal':
                    if type(value)==type(obj):
                        value=value.name
                    value = value or ''
                    event.add(field.name).value = value or ''
                elif ICS_TAGS[field.name]=='date' and value:
                    if field.name == 'dtstart':
                        date_start = start_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(value , "%Y-%m-%d %H:%M:%S")))
                    if field.name == 'dtend' and isinstance(value, float):
                        value = (start_date + datetime.timedelta(hours=value)).strftime('%Y-%m-%d %H:%M:%S')
                    if len(value)==10:
                        value = ics_datetime(value, True)
                    else:
                        value = ics_datetime(value)
                    event.add(field.name).value = value
        s= StringIO.StringIO(cal.serialize())
        s.name = node
        cr.commit()
        return s
document_directory_content()

class crm_case(osv.osv):
    _inherit = 'crm.case'
    _columns = {
        'code': fields.char('Calendar Code', size=64),
        'date_deadline': fields.datetime('Deadline', help="Deadline Date is automatically computed from Start Date + Duration"),
    }

    _defaults = {
        'code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'crm.case'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        """
        code field must be unique in ICS file
        """
        if not default: default = {}
        if not context: context = {}
        default.update({'code': self.pool.get('ir.sequence').get(cr, uid, 'crm.case'), 'id': False})
        return super(crm_case, self).copy(cr, uid, id, default, context)

    def on_change_duration(self, cr, uid, id, date, duration):
        if not date:
            return {}
        start_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, "%Y-%m-%d %H:%M:%S")))
        if duration >= 0 :
            end = start_date + datetime.timedelta(hours=duration)
        if duration < 0:
            raise osv.except_osv(_('Warning !'),
                    _('You can not set negative Duration.'))

        res = {'value' : {'date_deadline' : end.strftime('%Y-%m-%d %H:%M:%S')}}
        return res

crm_case()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

