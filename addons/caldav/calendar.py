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

from datetime import datetime, timedelta
from dateutil import parser
from dateutil.rrule import *
from osv import osv, fields
from tools.translate import _
import base64
import math
import pooler
import pytz
import re
import tools
import time


try:
    import vobject
except ImportError:
    raise osv.except_osv('vobject Import Error!','Please install python-vobject \
                     from http://vobject.skyhouseconsulting.com/')

# O-1  Optional and can come only once
# O-n  Optional and can come more than once
# R-1  Required and can come only once
# R-n  Required and can come more than once

def uid2openobjectid(cr, uidval, oomodel, rdate):
    """ UID To Open Object Id
        @param cr: the current row, from the database cursor,
        @param uidval: Get USerId vale
        @oomodel: Open Object ModelName
        @param rdate: Get Recurrent Date
    """
    __rege = re.compile(r'OpenObject-([\w|\.]+)_([0-9]+)@(\w+)$')
    wematch = __rege.match(uidval.encode('utf8'))
    if not wematch:
        return (False, None)
    else:
        model, id, dbname = wematch.groups()
        model_obj = pooler.get_pool(cr.dbname).get(model)
        if (not model == oomodel) or (not dbname == cr.dbname):
            return (False, None)
        qry = 'select distinct(id) from %s' % model_obj._table
        if rdate:
            qry += " where recurrent_id='%s'" % (rdate)
            cr.execute(qry)
            r_id = cr.fetchone()
            if r_id:
                return (id, r_id[0])
        cr.execute(qry)
        ids = map(lambda x: str(x[0]), cr.fetchall())
        if id in ids:
            return (id, None)
        return (False, None)

def openobjectid2uid(cr, uidval, oomodel):
    """ Open Object Id To UId
        @param cr: the current row, from the database cursor,
        @param uidval: Get USerId vale
        @oomodel: Open Object ModelName """

    value = 'OpenObject-%s_%s@%s' % (oomodel, uidval, cr.dbname)
    return value

def get_attribute_mapping(cr, uid, calname, context={}):
    """ Attribute Mapping with Basic calendar fields and lines
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param calname: Get Calendar name
        @param context: A standard dictionary for contextual values """

    if not context:
        context = {}
    pool = pooler.get_pool(cr.dbname)
    field_obj = pool.get('basic.calendar.fields')
    type_obj = pool.get('basic.calendar.lines')
    domain = [('object_id.model', '=', context.get('model'))]
    if context.get('calendar_id'):
        domain.append(('calendar_id', '=', context.get('calendar_id')))
    type_id = type_obj.search(cr, uid, domain)
    fids = field_obj.search(cr, uid, [('type_id', '=', type_id[0])])
    res = {}
    for field in field_obj.browse(cr, uid, fids):
        attr = field.name.name
        res[attr] = {}
        res[attr]['field'] = field.field_id.name
        res[attr]['type'] = field.field_id.ttype
        if field.fn == 'hours':
            res[attr]['type'] = "timedelta"
        if res[attr]['type'] in ('one2many', 'many2many', 'many2one'):
            res[attr]['object'] = field.field_id.relation
        elif res[attr]['type'] in ('selection') and field.mapping:
            res[attr]['mapping'] = eval(field.mapping)
    if not res.get('uid', None):
        res['uid'] = {}
        res['uid']['field'] = 'id'
        res['uid']['type'] = "integer"
    return res

def map_data(cr, uid, obj):
    """ Map Data
        @param self: The object pointer
        @param cr: the current row, from the database cursor,"""

    vals = {}
    for map_dict in obj.__attribute__:
        map_val = obj.ical_get(map_dict, 'value')
        field = obj.ical_get(map_dict, 'field')
        field_type = obj.ical_get(map_dict, 'type')
        if field:
            if field_type == 'selection':
                if not map_val:
                    continue
                mapping = obj.__attribute__[map_dict].get('mapping', False)
                if mapping:
                    map_val = mapping[map_val.lower()]
                else:
                    map_val = map_val.lower()
            if field_type == 'many2many':
                ids = []
                if not map_val:
                    vals[field] = ids
                    continue
                model = obj.__attribute__[map_dict].get('object', False)
                modobj = obj.pool.get(model)
                for map_vall in map_val:
                    id = modobj.create(cr, uid, map_vall)
                    ids.append(id)
                vals[field] = [(6, 0, ids)]
                continue
            if field_type == 'many2one':
                id = None
                if not map_val or not isinstance(map_val, dict):
                    vals[field] = id
                    continue
                model = obj.__attribute__[map_dict].get('object', False)
                modobj = obj.pool.get(model)
                id = modobj.create(cr, uid, map_val)
                vals[field] = id
                continue
            if field_type == 'timedelta':
                if map_val:
                    vals[field] = (map_val.seconds/float(86400) + map_val.days)
            if map_val:
                vals[field] = map_val
    return vals

class CalDAV(object):
    __attribute__ = {}



    def ical_set(self, name, value, type):
        """ set calendar Attribute
         @param self: The object pointer,
         @param name: Get Attribute Name
         @param value: Get Attribute Value
         @param type: Get Attribute Type
        """
        if name in self.__attribute__ and self.__attribute__[name]:
            self.__attribute__[name][type] = value
        return True

    def ical_get(self, name, type):
        """ Get calendar Attribute
         @param self: The object pointer,
         @param name: Get Attribute Name
         @param type: Get Attribute Type
        """

        if self.__attribute__.get(name):
            val = self.__attribute__.get(name).get(type, None)
            valtype =  self.__attribute__.get(name).get('type', None)
            if type == 'value':
                if valtype and valtype == 'datetime' and val:
                    if isinstance(val, list):
                        val = ','.join(map(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'), val))
                    else:
                        val = val.strftime('%Y-%m-%d %H:%M:%S')
            return  val
        else:
            return  self.__attribute__.get(name, None)

    def ical_reset(self, type):
        """ Reset Calendar Attribute
         @param self: The object pointer,
         @param type: Get Attribute Type
        """

        for name in self.__attribute__:
            if self.__attribute__[name]:
                self.__attribute__[name][type] = None
        return True

    def parse_ics(self, cr, uid, child, cal_children=None, context=None):
        """ parse calendaring and scheduling information
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values """

        att_data = []
        for cal_data in child.getChildren():
            if cal_data.name.lower() == 'attendee':
                ctx = context.copy()
                if cal_children:
                    ctx.update({'model': cal_children[cal_data.name.lower()]})
                attendee = self.pool.get('basic.calendar.attendee')
                att_data.append(attendee.import_cal(cr, uid, cal_data, context=ctx))
                self.ical_set(cal_data.name.lower(), att_data, 'value')
                continue
            if cal_data.name.lower() == 'valarm':
                alarm = self.pool.get('basic.calendar.alarm')
                ctx = context.copy()
                if cal_children:
                    ctx.update({'model': cal_children[cal_data.name.lower()]})
                vals = alarm.import_cal(cr, uid, cal_data, context=ctx)
                self.ical_set(cal_data.name.lower(), vals, 'value')
                continue
            if cal_data.name.lower() == 'exdate':
                exval = map(lambda x: str(x), cal_data.value)
                self.ical_set(cal_data.name.lower(), ','.join(exval), 'value')
                continue
            if cal_data.name.lower() in self.__attribute__:

                if cal_data.params.get('X-VOBJ-ORIGINAL-TZID'):
                    self.ical_set('vtimezone', cal_data.params.get('X-VOBJ-ORIGINAL-TZID'), 'value')
                self.ical_set(cal_data.name.lower(), cal_data.value, 'value')
        vals = map_data(cr, uid, self)
        return vals

    def create_ics(self, cr, uid, datas, name, ical, context=None):
        """ create calendaring and scheduling information
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values """

        if not datas:
            return
        timezones = []
        for data in datas:
            tzval = None
            vevent = ical.add(name)
            for field in self.__attribute__.keys():
                map_field = self.ical_get(field, 'field')
                map_type = self.ical_get(field, 'type')
                if map_field in data.keys():
                    if field == 'uid':
                        model = context.get('model', None)
                        if not model:
                            continue
                        uidval = openobjectid2uid(cr, data[map_field], model)
                        model_obj = self.pool.get(model)
                        r_ids = []
                        if model_obj._columns.get('recurrent_uid', None):
                            cr.execute('select id from %s  where recurrent_uid=%s'
                                           % (model_obj._table, data[map_field]))
                            r_ids = map(lambda x: x[0], cr.fetchall())
                        if r_ids:
                            rdata = self.pool.get(model).read(cr, uid, r_ids)
                            event_obj = self.pool.get('basic.calendar.event')
                            rcal = event_obj.export_cal(cr, uid, rdata, context=context)
                            for revents in rcal.contents['vevent']:
                                ical.contents['vevent'].append(revents)
                        if data.get('recurrent_uid', None):
                            uidval = openobjectid2uid(cr, data['recurrent_uid'], model)
                        vevent.add('uid').value = uidval
                    elif field == 'attendee' and data[map_field]:
                        model = self.__attribute__[field].get('object', False)
                        attendee_obj = self.pool.get('basic.calendar.attendee')
                        vevent = attendee_obj.export_cal(cr, uid, model, \
                                     data[map_field], vevent, context=context)
                    elif field == 'valarm' and data[map_field]:
                        model = self.__attribute__[field].get('object', False)
                        ctx = context.copy()
                        ctx.update({'model': model})
                        alarm_obj = self.pool.get('basic.calendar.alarm')
                        vevent = alarm_obj.export_cal(cr, uid, model, \
                                    data[map_field][0], vevent, context=ctx)
                    elif field == 'vtimezone' and data[map_field] and data[map_field] not in timezones:
                        tzval = data[map_field]
                        tz_obj = self.pool.get('basic.calendar.timezone')
                        ical = tz_obj.export_cal(cr, uid, None, \
                                     data[map_field], ical, context=context)
                        timezones.append(data[map_field])
                    elif data[map_field]:
                        if map_type in ("char", "text"):
                            if field in ('exdate'):
                                vevent.add(field).value = map(parser.parse, (data[map_field]).split(','))
                            else:
                                vevent.add(field).value = tools.ustr(data[map_field])
                        elif map_type in ('datetime', 'date') and data[map_field]:
                            dtfield = vevent.add(field)
                            dtfield.value = parser.parse(data[map_field])
                            if tzval:
                                dtfield.params['TZID'] = [tzval.title()]
                        elif map_type == "timedelta":
                            vevent.add(field).value = timedelta(hours=data[map_field])
                        elif map_type == "many2one":
                            vevent.add(field).value = tools.ustr(data.get(map_field)[1])
                        elif map_type in ("float", "integer"):
                            vevent.add(field).value = str(data.get(map_field))
                        elif map_type == "selection":
                            if not self.ical_get(field, 'mapping'):
                                vevent.add(field).value = (tools.ustr(data[map_field])).upper()
                            else:
                                for key1, val1 in self.ical_get(field, 'mapping').items():
                                    if val1 == data[map_field]:
                                        vevent.add(field).value = key1
        return vevent

    def check_import(self, cr, uid, vals, context={}):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
            @param context: A standard dictionary for contextual values
        """

        ids = []
        model_obj = self.pool.get(context.get('model'))
        recur_pool = {}
        try:
            for val in vals:
                exists, r_id = uid2openobjectid(cr, val['id'], context.get('model'), \
                                                                 val.get('recurrent_id'))
                if val.has_key('create_date'): val.pop('create_date')
                u_id = val.get('id', None)
                val.pop('id')
                if exists and r_id:
                    val.update({'recurrent_uid': exists})
                    model_obj.write(cr, uid, [r_id], val)
                    ids.append(r_id)
                elif exists:
                    model_obj.write(cr, uid, [exists], val)
                    ids.append(exists)
                else:
                    if u_id in recur_pool and val.get('recurrent_id'):
                        val.update({'recurrent_uid': recur_pool[u_id]})
                        revent_id = model_obj.create(cr, uid, val)
                        ids.append(revent_id)
                    else:
                        event_id = model_obj.create(cr, uid, val)
                        recur_pool[u_id] = event_id
                        ids.append(event_id)
        except Exception, e:
            raise osv.except_osv(('Error !'), (str(e)))
        return ids

    def export_cal(self, cr, uid, datas, vobj=None, context={}):
        """ Export Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param datas: Get Data's for caldav
            @param context: A standard dictionary for contextual values
        """

        try:
            self.__attribute__ = get_attribute_mapping(cr, uid, self._calname, context)
            ical = vobject.iCalendar()
            self.create_ics(cr, uid, datas, vobj, ical, context=context)
            return ical
        except Exception, e:
            raise osv.except_osv(('Error !'), (str(e)))

    def import_cal(self, cr, uid, content, data_id=None, context=None):
        """ Import Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param data_id: Get Data’s ID or False
            @param context: A standard dictionary for contextual values
        """

        ical_data = base64.decodestring(content)
        self.__attribute__ = get_attribute_mapping(cr, uid, self._calname, context)
        parsedCal = vobject.readOne(ical_data)
        res = []
        vals = {}
        for child in parsedCal.getChildren():
            if child.name.lower() in ('vevent', 'vtodo'):
                vals = self.parse_ics(cr, uid, child, context=context)
            else:
                vals = {}
                continue
            if vals: res.append(vals)
            self.ical_reset('value')
        return res

class calendar_collection(osv.osv):
    _inherit = 'document.directory' 
    _columns = {
        'calendar_collection' : fields.boolean('Calendar Collection'),
        'calendar_ids': fields.one2many('basic.calendar', 'collection_id', 'Calendars'),
    }
    _default = {
        'calendar_collection' : False,
    }
    
calendar_collection()

class Calendar(CalDAV, osv.osv):
    _name = 'basic.calendar'    
    _calname = 'calendar'

    __attribute__ = {
        'prodid': None, # Use: R-1, Type: TEXT, Specifies the identifier for the product that created the iCalendar object.
        'version': None, # Use: R-1, Type: TEXT, Specifies the identifier corresponding to the highest version number
                           #             or the minimum and maximum range of the iCalendar specification
                           #             that is required in order to interpret the iCalendar object.
        'calscale': None, # Use: O-1, Type: TEXT, Defines the calendar scale used for the calendar information specified in the iCalendar object.
        'method': None, # Use: O-1, Type: TEXT, Defines the iCalendar object method associated with the calendar object.
        'vevent': None, # Use: O-n, Type: Collection of Event class
        'vtodo': None, # Use: O-n, Type: Collection of ToDo class
        'vjournal': None, # Use: O-n, Type: Collection of Journal class
        'vfreebusy': None, # Use: O-n, Type: Collection of FreeBusy class
        'vtimezone': None, # Use: O-n, Type: Collection of Timezone class
    }
    _columns = {
            'name': fields.char("Name", size=64),
            'collection_id': fields.many2one('document.directory', 'Collection', \
                                       required=True),
            'user_id': fields.many2one('res.users', 'Owner'),
            'line_ids': fields.one2many('basic.calendar.lines', 'calendar_id', 'Calendar Lines'),            
            'create_date': fields.datetime('Created Date'),
            'write_date': fields.datetime('Modifided Date'),
    }   

    def export_cal(self, cr, uid, ids, vobj='vevent', context={}):
        """ Export Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of calendar’s IDs
            @param context: A standard dictionary for contextual values
        """

        cal = self.browse(cr, uid, ids[0])
        ical = vobject.iCalendar()
        for line in cal.line_ids:
            if line.name in ('valarm', 'attendee'):
                continue
            mod_obj = self.pool.get(line.object_id.model)
            data_ids = mod_obj.search(cr, uid, eval(line.domain), context=context)
            datas = mod_obj.read(cr, uid, data_ids, context=context)
            context.update({'model': line.object_id.model,
                                    'calendar_id': cal.id
                                    })
            self.__attribute__ = get_attribute_mapping(cr, uid, line.name, context)
            self.create_ics(cr, uid, datas, line.name, ical, context=context)
        return ical.serialize()

    def import_cal(self, cr, uid, content, data_id=None, context=None):
        """ Import Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param data_id: Get Data’s ID or False
            @param context: A standard dictionary for contextual values
        """

        if not context:
            context = {}
        vals = []
        ical_data = base64.decodestring(content)
        parsedCal = vobject.readOne(ical_data)
        if not data_id:
            data_id = self.search(cr, uid, [])[0]
        cal = self.browse(cr, uid, data_id)
        cal_children = {}
        count = 0
        for line in cal.line_ids:
            cal_children[line.name] = line.object_id.model
        for child in parsedCal.getChildren():
            if child.name.lower() in cal_children:
                context.update({'model': cal_children[child.name.lower()],
                                'calendar_id': cal.id
                                })
                self.__attribute__ = get_attribute_mapping(cr, uid, child.name.lower(), context=context)
                val = self.parse_ics(cr, uid, child, cal_children=cal_children, context=context)
                vals.append(val)
                obj = self.pool.get(cal_children[child.name.lower()])
        if hasattr(obj, 'check_import'):
            obj.check_import(cr, uid, vals, context=context)
        else:
            self.check_import(cr, uid, vals, context=context)
        return {}
Calendar()


class basic_calendar_line(osv.osv):
    """ Calendar Lines """

    _name = 'basic.calendar.lines'
    _description = 'Calendar Lines'

    _columns = {
            'name': fields.selection([('vevent', 'Event'), ('vtodo', 'TODO'), \
                                    ('valarm', 'Alarm'), \
                                    ('attendee', 'Attendee')], \
                                    string="Type", size=64),
            'object_id': fields.many2one('ir.model', 'Object'),
            'calendar_id': fields.many2one('basic.calendar', 'Calendar', \
                                       required=True, ondelete='cascade'),
            'domain': fields.char('Domain', size=124),
            'mapping_ids': fields.one2many('basic.calendar.fields', 'type_id', 'Fields Mapping')
    }

    _defaults = {
        'domain': lambda *a: '[]',
    }

    def create(self, cr, uid, vals, context={}):
        """ create calendar's line
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get the Values
            @param context: A standard dictionary for contextual values
        """

        cr.execute("Select count(id) from basic_calendar_lines \
                                where name='%s' and calendar_id=%s" % (vals.get('name'), vals.get('calendar_id')))
        res = cr.fetchone()
        if res:
            if res[0] > 0:
                raise osv.except_osv(_('Warning !'), _('Can not create \
line "%s" more than once' % (vals.get('name'))))
        return super(basic_calendar_line, self).create(cr, uid, vals, context=context)

basic_calendar_line()


class basic_calendar_attribute(osv.osv):
    _name = 'basic.calendar.attributes'
    _description = 'Calendar attributes'
    _columns = {
        'name': fields.char("Name", size=64, required=True),
        'type': fields.selection([('vevent', 'Event'), ('vtodo', 'TODO'), \
                                    ('alarm', 'Alarm'), \
                                    ('attendee', 'Attendee')], \
                                    string="Type", size=64, required=True),
    }

basic_calendar_attribute()


class basic_calendar_fields(osv.osv):
    """ Calendar fields """

    _name = 'basic.calendar.fields'
    _description = 'Calendar fields'

    _columns = {
        'field_id': fields.many2one('ir.model.fields', 'OpenObject Field'),
        'name': fields.many2one('basic.calendar.attributes', 'Name', required=True),
        'type_id': fields.many2one('basic.calendar.lines', 'Type', \
                                   required=True, ondelete='cascade'),
        'expr': fields.char("Expression", size=64),
        'fn': fields.selection([('field', 'Use the field'),
                        ('const', 'Expression as constant'),
                        ('hours', 'Interval in hours'),
                        ], 'Function'),
        'mapping': fields.text('Mapping'),
    }

    _defaults = {
        'fn': lambda *a: 'field',
    }

    def check_line(self, cr, uid, vals, name, context=None):
        """ check calendar's line
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
            @param context: A standard dictionary for contextual values
        """
        f_obj = self.pool.get('ir.model.fields')
        field = f_obj.browse(cr, uid, vals['field_id'], context=context)
        relation = field.relation
        line_obj = self.pool.get('basic.calendar.lines')
        l_id = line_obj.search(cr, uid, [('name', '=', name)])
        if l_id:
            line = line_obj.browse(cr, uid, l_id, context=context)[0]
            line_rel = line.object_id.model
            if (relation != 'NULL') and (not relation == line_rel):
                raise osv.except_osv(_('Warning !'), _('Please provide proper configuration of "%s" in Calendar Lines' % (name)))
        return True

    def create(self, cr, uid, vals, context={}):
        """ Create Calendar's fields
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
            @param context: A standard dictionary for contextual values
        """

        cr.execute('select name from basic_calendar_attributes \
                            where id=%s' % (vals.get('name')))
        name = cr.fetchone()
        name = name[0]
        if name in ('valarm', 'attendee'):
            self.check_line(cr, uid, vals, name, context=context)
        cr.execute("Select count(id) from basic_calendar_fields \
                                where name=%s and type_id=%s" % (vals.get('name'), vals.get('type_id')))
        res = cr.fetchone()
        if res:
            if res[0] > 0:
                raise osv.except_osv(_('Warning !'), _('Can not map the field more than once'))
        return super(basic_calendar_fields, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """ write Calendar's fields
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
            @param context: A standard dictionary for contextual values
        """

        if not vals:
            return
        for id in ids:
            field = self.browse(cr, uid, id, context=context)
            name = field.name.name
            if name in ('valarm', 'attendee'):
                self.check_line(cr, uid, vals, name, context=context)
            qry = "Select count(id) from basic_calendar_fields \
                                where name=%s and type_id=%s" % (field.name.id, field.type_id.id)
            cr.execute(qry)
            res = cr.fetchone()
            if res:
                if res[0] > 1:
                    raise osv.except_osv(_('Warning !'), _('Can not map same field more than once'))
        return super(basic_calendar_fields, self).write(cr, uid, ids, vals, context)

basic_calendar_fields()


class Event(CalDAV, osv.osv_memory):
    _name = 'basic.calendar.event'
    _calname = 'vevent'
    __attribute__ = {
        'class': None, # Use: O-1, Type: TEXT, Defines the access classification for a calendar  component like "PUBLIC" / "PRIVATE" / "CONFIDENTIAL"
        'created': None, # Use: O-1, Type: DATE-TIME, Specifies the date and time that the calendar information  was created by the calendar user agent in the calendar store.
        'description': None, # Use: O-1, Type: TEXT, Provides a more complete description of the calendar component, than that provided by the "SUMMARY" property.
        'dtstart': None, # Use: O-1, Type: DATE-TIME, Specifies when the calendar component begins.
        'geo': None, # Use: O-1, Type: FLOAT, Specifies information related to the global position for the activity specified by a calendar component.
        'last-mod': None, # Use: O-1, Type: DATE-TIME        Specifies the date and time that the information associated with the calendar component was last revised in the calendar store.
        'location': None, # Use: O-1, Type: TEXT            Defines the intended venue for the activity defined by a calendar component.
        'organizer': None, # Use: O-1, Type: CAL-ADDRESS, Defines the organizer for a calendar component.
        'priority': None, # Use: O-1, Type: INTEGER, Defines the relative priority for a calendar component.
        'dtstamp': None, # Use: O-1, Type: DATE-TIME, Indicates the date/time that the instance of the iCalendar object was created.
        'seq': None, # Use: O-1, Type: INTEGER, Defines the revision sequence number of the calendar component within a sequence of revision.
        'status': None, # Use: O-1, Type: TEXT, Defines the overall status or confirmation for the calendar component.
        'summary': None, # Use: O-1, Type: TEXT, Defines a short summary or subject for the calendar component.
        'transp': None, # Use: O-1, Type: TEXT, Defines whether an event is transparent or not to busy time searches.
        'uid': None, # Use: O-1, Type: TEXT, Defines the persistent, globally unique identifier for the calendar component.
        'url': None, # Use: O-1, Type: URL, Defines a Uniform Resource Locator (URL) associated with the iCalendar object.
        'recurid': None,
        'attach': None, # Use: O-n, Type: BINARY, Provides the capability to associate a document object with a calendar component.
        'attendee': None, # Use: O-n, Type: CAL-ADDRESS, Defines an "Attendee" within a calendar component.
        'categories': None, # Use: O-n, Type: TEXT, Defines the categories for a calendar component.
        'comment': None, # Use: O-n, Type: TEXT, Specifies non-processing information intended to provide a comment to the calendar user.
        'contact': None, # Use: O-n, Type: TEXT, Used to represent contact information or alternately a  reference to contact information associated with the calendar component.
        'exdate': None, # Use: O-n, Type: DATE-TIME, Defines the list of date/time exceptions for a recurring calendar component.
        'exrule': None, # Use: O-n, Type: RECUR, Defines a rule or repeating pattern for an exception to a recurrence set.
        'rstatus': None,
        'related': None, # Use: O-n, Specify the relationship of the alarm trigger with respect to the start or end of the calendar component.
                                #  like A trigger set 5 minutes after the end of the event or to-do.---> TRIGGER;related=END:PT5M
        'resources': None, # Use: O-n, Type: TEXT, Defines the equipment or resources anticipated for an activity specified by a calendar entity like RESOURCES:EASEL,PROJECTOR,VCR, LANGUAGE=fr:1 raton-laveur
        'rdate': None, # Use: O-n, Type: DATE-TIME, Defines the list of date/times for a recurrence set.
        'rrule': None, # Use: O-n, Type: RECUR, Defines a rule or repeating pattern for recurring events, to-dos, or time zone definitions.
        'x-prop': None,
        'duration': None, # Use: O-1, Type: DURATION, Specifies a positive duration of time.
        'dtend': None, # Use: O-1, Type: DATE-TIME, Specifies the date and time that a calendar component ends.
    }

    def export_cal(self, cr, uid, datas, vobj='vevent', context={}):
        """ Export calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param datas: Get datas
            @param context: A standard dictionary for contextual values
        """

        return super(Event, self).export_cal(cr, uid, datas, 'vevent', context=context)

Event()


class ToDo(CalDAV, osv.osv_memory):
    _name = 'basic.calendar.todo'
    _calname = 'vtodo'

    __attribute__ = {
                'class': None,
                'completed': None,
                'created': None,
                'description': None,
                'dtstamp': None,
                'dtstart': None,
                'duration': None,
                'due': None,
                'geo': None,
                'last-mod ': None,
                'location': None,
                'organizer': None,
                'percent': None,
                'priority': None,
                'recurid': None,
                'seq': None,
                'status': None,
                'summary': None,
                'uid': None,
                'url': None,
                'attach': None,
                'attendee': None,
                'categories': None,
                'comment': None,
                'contact': None,
                'exdate': None,
                'exrule': None,
                'rstatus': None,
                'related': None,
                'resources': None,
                'rdate': None,
                'rrule': None,
            }

    def export_cal(self, cr, uid, datas, vobj='vevent', context={}):
        """ Export Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param datas: Get datas
            @param context: A standard dictionary for contextual values
        """

        return super(ToDo, self).export_cal(cr, uid, datas, 'vtodo', context=context)

ToDo()


class Journal(CalDAV):
    __attribute__ = {
    }


class FreeBusy(CalDAV):
    __attribute__ = {
    'contact': None, # Use: O-1, Type: Text, Represent contact information or alternately a  reference to contact information associated with the calendar component.
    'dtstart': None, # Use: O-1, Type: DATE-TIME, Specifies when the calendar component begins.
    'dtend': None, # Use: O-1, Type: DATE-TIME, Specifies the date and time that a calendar component ends.
    'duration': None, # Use: O-1, Type: DURATION, Specifies a positive duration of time.
    'dtstamp': None, # Use: O-1, Type: DATE-TIME, Indicates the date/time that the instance of the iCalendar object was created.
    'organizer': None, # Use: O-1, Type: CAL-ADDRESS, Defines the organizer for a calendar component.
    'uid': None, # Use: O-1, Type: Text, Defines the persistent, globally unique identifier for the calendar component.
    'url': None, # Use: O-1, Type: URL, Defines a Uniform Resource Locator (URL) associated with the iCalendar object.
    'attendee': None, # Use: O-n, Type: CAL-ADDRESS, Defines an "Attendee" within a calendar component.
    'comment': None, # Use: O-n, Type: TEXT, Specifies non-processing information intended to provide a comment to the calendar user.
    'freebusy': None, # Use: O-n, Type: PERIOD, Defines one or more free or busy time intervals.
    'rstatus': None,
    'X-prop': None,
    }


class Timezone(CalDAV, osv.osv_memory):
    _name = 'basic.calendar.timezone'
    _calname = 'vtimezone'

    __attribute__ = {
    'tzid': {'field': 'tzid'}, # Use: R-1, Type: Text, Specifies the text value that uniquely identifies the "VTIMEZONE" calendar component.
    'last-mod': None, # Use: O-1, Type: DATE-TIME, Specifies the date and time that the information associated with the calendar component was last revised in the calendar store.
    'tzurl': None, # Use: O-1, Type: URI, Provides a means for a VTIMEZONE component to point to a network location that can be used to retrieve an up-to-date version of itself.
    'standardc': {'tzprop': None}, # Use: R-1,
    'daylightc': {'tzprop': None}, # Use: R-1,
    'x-prop': None, # Use: O-n, Type: Text,
    }

    def get_name_offset(self, cr, uid, tzid, context={}):
        """ Get Name Offset value
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param context: A standard dictionary for contextual values
        """

        mytz = pytz.timezone(tzid.title())
        mydt = datetime.now(tz=mytz)
        offset = mydt.utcoffset()
        val = offset.days * 24 + float(offset.seconds) / 3600
        realoffset = '%02d%02d' % (math.floor(abs(val)), \
                                 round(abs(val) % 1 + 0.01, 2) * 60)
        realoffset = (val < 0 and ('-' + realoffset) or ('+' + realoffset))
        return (mydt.tzname(), realoffset)

    def export_cal(self, cr, uid, model, tzid, ical, context={}):
        """ Export Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param model: Get Model's name
            @param context: A standard dictionary for contextual values
        """

        ctx = context.copy()
        ctx.update({'model': model})
        cal_tz = ical.add('vtimezone')
        cal_tz.add('TZID').value = tzid.title()
        tz_std = cal_tz.add('STANDARD')
        tzname, offset = self.get_name_offset(cr, uid, tzid)
        tz_std.add("TZOFFSETFROM").value = offset
        tz_std.add("TZOFFSETTO").value = offset
        tz_std.add("DTSTART").value = datetime.now() # TODO
        tz_std.add("TZNAME").value = tzname
        return ical

    def import_cal(self, cr, uid, ical_data, context=None):
        """ Import Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ical_data: Get calendar's data
            @param context: A standard dictionary for contextual values
        """

        for child in ical_data.getChildren():
            if child.name.lower() == 'tzid':
                tzname = child.value
                self.ical_set(child.name.lower(), tzname, 'value')
        vals = map_data(cr, uid, self)
        return vals

Timezone()


class Alarm(CalDAV, osv.osv_memory):
    _name = 'basic.calendar.alarm'
    _calname = 'alarm'

    __attribute__ = {
    'action': None, # Use: R-1, Type: Text, defines the action to be invoked when an alarm is triggered LIKE "AUDIO" / "DISPLAY" / "EMAIL" / "PROCEDURE"
    'description': None, #      Type: Text, Provides a more complete description of the calendar component, than that provided by the "SUMMARY" property. Use:- R-1 for DISPLAY,Use:- R-1 for EMAIL,Use:- R-1 for PROCEDURE
    'summary': None, # Use: R-1, Type: Text        Which contains the text to be used as the message subject. Use for EMAIL
    'attendee': None, # Use: R-n, Type: CAL-ADDRESS, Contain the email address of attendees to receive the message. It can also include one or more. Use for EMAIL
    'trigger': None, # Use: R-1, Type: DURATION, The "TRIGGER" property specifies a duration prior to the start of an event or a to-do. The "TRIGGER" edge may be explicitly set to be relative to the "START" or "END" of the event or to-do with the "related" parameter of the "TRIGGER" property. The "TRIGGER" property value type can alternatively be set to an absolute calendar date and time of day value. Use for all action like AUDIO, DISPLAY, EMAIL and PROCEDURE
    'duration': None, #           Type: DURATION, Duration' and 'repeat' are both optional, and MUST NOT occur more than once each, but if one occurs, so MUST the other. Use:- 0-1 for AUDIO, EMAIL and PROCEDURE, Use:- 0-n for DISPLAY
    'repeat': None, #           Type: INTEGER, Duration' and 'repeat' are both optional, and MUST NOT occur more than once each, but if one occurs, so MUST the other. Use:- 0-1 for AUDIO, EMAIL and PROCEDURE, Use:- 0-n for DISPLAY
    'attach': None, # Use:- O-n: which MUST point to a sound resource, which is rendered when the alarm is triggered for AUDIO, Use:- O-n: which are intended to be sent as message attachments for EMAIL, Use:- R-1:which MUST point to a procedure resource, which is invoked when the alarm is triggered for PROCEDURE.
    'x-prop': None,
    }

    def export_cal(self, cr, uid, model, alarm_id, vevent, context={}):
        """ Export Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param model: Get Model's name
            @param alarm_id: Get Alarm's Id
            @param context: A standard dictionary for contextual values
        """

        valarm = vevent.add('valarm')
        alarm_object = self.pool.get(model)
        alarm_data = alarm_object.read(cr, uid, alarm_id, [])

        # Compute trigger data
        interval = alarm_data['trigger_interval']
        occurs = alarm_data['trigger_occurs']
        duration = (occurs == 'after' and alarm_data['trigger_duration']) \
                                        or -(alarm_data['trigger_duration'])
        related = alarm_data['trigger_related']
        trigger = valarm.add('TRIGGER')
        trigger.params['related'] = [related.upper()]
        if interval == 'days':
            delta = timedelta(days=duration)
        if interval == 'hours':
            delta = timedelta(hours=duration)
        if interval == 'minutes':
            delta = timedelta(minutes=duration)
        trigger.value = delta

        # Compute other details
        valarm.add('DESCRIPTION').value = alarm_data['name'] or 'OpenERP'
        valarm.add('ACTION').value = alarm_data['action']
        return vevent

    def import_cal(self, cr, uid, ical_data, context=None):
        """ Import Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ical_data: Get calendar's Data
            @param context: A standard dictionary for contextual values
        """

        ctx = context.copy()
        ctx.update({'model': context.get('model', None)})
        self.__attribute__ = get_attribute_mapping(cr, uid, self._calname, ctx)
        for child in ical_data.getChildren():
            if child.name.lower() == 'trigger':
                seconds = child.value.seconds
                days = child.value.days
                diff = (days * 86400) +  seconds
                interval = 'days'
                related = 'before'
                if not seconds:
                    duration = abs(days)
                    related = days > 0 and 'after' or 'before'
                elif (abs(diff) / 3600) == 0:
                    duration = abs(diff / 60)
                    interval = 'minutes'
                    related = days >= 0 and 'after' or 'before'
                else:
                    duration = abs(diff / 3600)
                    interval = 'hours'
                    related = days >= 0 and 'after' or 'before'
                self.ical_set('trigger_interval', interval, 'value')
                self.ical_set('trigger_duration', duration, 'value')
                self.ical_set('trigger_occurs', related.lower(), 'value')
                if child.params:
                    if child.params.get('related'):
                        self.ical_set('trigger_related', child.params.get('related')[0].lower(), 'value')
            else:
                self.ical_set(child.name.lower(), child.value.lower(), 'value')
        vals = map_data(cr, uid, self)
        return vals

Alarm()


class Attendee(CalDAV, osv.osv_memory):
    _name = 'basic.calendar.attendee'
    _calname = 'attendee'

    __attribute__ = {
    'cutype': None, # Use: 0-1    Specify the type of calendar user specified by the property like "INDIVIDUAL"/"GROUP"/"RESOURCE"/"ROOM"/"UNKNOWN".
    'member': None, # Use: 0-1    Specify the group or list membership of the calendar user specified by the property.
    'role': None, # Use: 0-1    Specify the participation role for the calendar user specified by the property like "CHAIR"/"REQ-PARTICIPANT"/"OPT-PARTICIPANT"/"NON-PARTICIPANT"
    'partstat': None, # Use: 0-1    Specify the participation status for the calendar user specified by the property. like use for VEVENT:- "NEEDS-ACTION"/"ACCEPTED"/"DECLINED"/"TENTATIVE"/"DELEGATED", use for VTODO:-"NEEDS-ACTION"/"ACCEPTED"/"DECLINED"/"TENTATIVE"/"DELEGATED"/"COMPLETED"/"IN-PROCESS" and use for VJOURNAL:- "NEEDS-ACTION"/"ACCEPTED"/"DECLINED".
    'rsvp': None, # Use: 0-1    Specify whether there is an expectation of a favor of a reply from the calendar user specified by the property value like TRUE / FALSE.
    'delegated-to': None, # Use: 0-1    Specify the calendar users to whom the calendar user specified by the property has delegated participation.
    'delegated-from': None, # Use: 0-1    Specify the calendar users that have delegated their participation to the calendar user specified by the property.
    'sent-by': None, # Use: 0-1    Specify the calendar user that is acting on behalf of the calendar user specified by the property.
    'cn': None, # Use: 0-1    Specify the common name to be associated with the calendar user specified by the property.
    'dir': None, # Use: 0-1    Specify reference to a directory entry associated with the calendar user specified by the property.
    'language': None, # Use: 0-1    Specify the language for text values in a property or property parameter.
    }

    def import_cal(self, cr, uid, ical_data, context=None):
        """ Import Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ical_data: Get calendar's Data
            @param context: A standard dictionary for contextual values
        """

        ctx = context.copy()
        ctx.update({'model': context.get('model', None)})
        self.__attribute__ = get_attribute_mapping(cr, uid, self._calname, ctx)
        for para in ical_data.params:
            if para.lower() == 'cn':
                self.ical_set(para.lower(), ical_data.params[para][0]+':'+ \
                        ical_data.value, 'value')
            else:
                self.ical_set(para.lower(), ical_data.params[para][0].lower(), 'value')
        if not ical_data.params.get('CN'):
            self.ical_set('cn', ical_data.value, 'value')
        vals = map_data(cr, uid, self)
        return vals

    def export_cal(self, cr, uid, model, attendee_ids, vevent, context={}):
        """ Export Calendar
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param model: Get model's name
            @param attendee_ids: Get Attendee's Id
            @param context: A standard dictionary for contextual values
        """

        attendee_object = self.pool.get(model)
        ctx = context.copy()
        ctx.update({'model': model})
        self.__attribute__ = get_attribute_mapping(cr, uid, self._calname, ctx)
        for attendee in attendee_object.read(cr, uid, attendee_ids, []):
            attendee_add = vevent.add('attendee')
            cn_val = ''
            for a_key, a_val in self.__attribute__.items():
                if attendee[a_val['field']] and a_val['field'] != 'cn':
                    if a_val['type'] in ('text', 'char', 'selection'):
                        attendee_add.params[a_key] = [str(attendee[a_val['field']])]
                    elif a_val['type'] == 'boolean':
                        attendee_add.params[a_key] = [str(attendee[a_val['field']])]
                if a_val['field'] == 'cn' and attendee[a_val['field']]:
                    cn_val = [str(attendee[a_val['field']])]
                    if cn_val:
                        attendee_add.params['CN'] = cn_val
            if not attendee['email']:
                raise osv.except_osv(_('Error !'), _('Attendee must have an Email Id'))
            elif attendee['email']:
                attendee_add.value = 'MAILTO:' + attendee['email']
        return vevent

Attendee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
