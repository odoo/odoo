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

from osv import fields, osv
from time import strftime
import time
import base64
import vobject
from dateutil.rrule import *
from dateutil import parser
from datetime import datetime
from time import strftime
from pytz import timezone
import tools

class crm_section(osv.osv):
    _name = 'crm.case.section'
    _inherit = 'crm.case.section'
    _description = 'Cases Section'

    def export_cal(self, cr, uid, ids, context={}):
        # Set all property of CalDAV
        self.export_ical()

    def import_cal(self, cr, uid, ids, context={}):
        self.import_ical(cr, uid)
        # get all property of CalDAV
crm_section()

class crm_caldav_attendee(osv.osv):
    _name = 'crm.caldav.attendee'
    _description = 'Attendee information'
    _rec_name = 'cutype'
    
    __attribute__ = {
        'cutype' : {'field':'cutype', 'type':'text'}, # Use: 0-1    Specify the type of calendar user specified by the property like "INDIVIDUAL"/"GROUP"/"RESOURCE"/"ROOM"/"UNKNOWN".
        'member' : {'field':'member', 'type':'text'}, # Use: 0-1    Specify the group or list membership of the calendar user specified by the property.
        'role' : {'field':'role', 'type':'text'}, # Use: 0-1    Specify the participation role for the calendar user specified by the property like "CHAIR"/"REQ-PARTICIPANT"/"OPT-PARTICIPANT"/"NON-PARTICIPANT"
        'partstat' : {'field':'partstat', 'type':'text'}, # Use: 0-1    Specify the participation status for the calendar user specified by the property. like use for VEVENT :- "NEEDS-ACTION"/"ACCEPTED"/"DECLINED"/"TENTATIVE"/"DELEGATED", use for VTODO :-"NEEDS-ACTION"/"ACCEPTED"/"DECLINED"/"TENTATIVE"/"DELEGATED"/"COMPLETED"/"IN-PROCESS" and use for VJOURNAL :- "NEEDS-ACTION"/"ACCEPTED"/"DECLINED".
        'rsvp' : {'field':'rsvp', 'type':'boolean'}, # Use: 0-1    Specify whether there is an expectation of a favor of a reply from the calendar user specified by the property value like TRUE / FALSE.
        'delegated-to' : {'field':'delegated_to', 'type':'char'}, # Use: 0-1    Specify the calendar users to whom the calendar user specified by the property has delegated participation.
        'delegated-from' : {'field':'delegated_from', 'type':'char'}, # Use: 0-1    Specify the calendar users that have delegated their participation to the calendar user specified by the property.
        'sent-by' : {'field':'sent_by', 'type':'text'}, # Use: 0-1    Specify the calendar user that is acting on behalf of the calendar user specified by the property.
        'cn' : {'field':'cn', 'type':'text'}, # Use: 0-1    Specify the common name to be associated with the calendar user specified by the property.
        'dir' : {'field':'dir', 'type':'text'}, # Use: 0-1    Specify reference to a directory entry associated with the calendar user specified by the property.
        'language' : {'field':'language', 'type':'text'}, # Use: 0-1    Specify the language for text values in a property or property parameter.
    }
     
    _columns = {
                'cutype' : fields.selection([('INDIVIDUAL', 'INDIVIDUAL'), ('GROUP', 'GROUP'), \
                        ('RESOURCE', 'RESOURCE'), ('ROOM', 'ROOM'), ('UNKNOWN', 'UNKNOWN') ], 'CUTYPE'), 
                'member' : fields.char('Member', size=124), 
                'role' : fields.selection([('CHAIR', 'CHAIR'), ('REQ-PARTICIPANT', 'REQ-PARTICIPANT'), \
                        ('OPT-PARTICIPANT', 'OPT-PARTICIPANT'), ('NON-PARTICIPANT', 'NON-PARTICIPANT')], 'ROLE'), 
                'partstat' : fields.selection([('NEEDS-ACTION', 'NEEDS-ACTION'), ('ACCEPTED', 'ACCEPTED'), \
                        ('DECLINED', 'DECLINED'), ('TENTATIVE', 'TENTATIVE'), ('DELEGATED', 'DELEGATED')], 'PARTSTAT'), 
                'rsvp' :  fields.boolean('RSVP'), 
                'delegated_to' : fields.char('DELEGATED-TO', size=124), 
                'delegated_from' : fields.char('DELEGATED-FROM', size=124), 
                'sent_by' : fields.char('SENT-BY', size=124), 
                'cn' : fields.char('CN', size=124), 
                'dir' : fields.char('DIR', size=124), 
                'language' : fields.char('LANGUAGE', size=124), 
                }

crm_caldav_attendee()

class crm_case(osv.osv):
    _name = 'crm.case'
    _inherit = 'crm.case'
    _description = 'Cases'
    
    __attribute__ = {
        'class' : {'field':'class', 'type':'text'}, 
        'created' : {'field':'create_date', 'type':'datetime'}, # keep none for now
        'description' : {'field':'description', 'type':'text'}, 
        'dtstart' : {'field':'date', 'type':'datetime'}, 
        #'last-mod' : {'field':'write_date', 'type':'datetime'}, 
        'location' : {'field':'location', 'type':'text'}, 
        'organizer' : {'field':'partner_id', 'sub-field':'name', 'type':'many2one'}, 
        'priority' : {'field':'priority', 'type':'int'}, 
        'dtstamp'  : {'field':'date', 'type':'datetime'}, 
        'seq' : None, 
        'status' : {'field':'state', 'type':'selection', 'mapping' : {'TENTATIVE' : 'draft', \
                                                  'CONFIRMED' : 'open' , 'CANCELLED' : 'cancel'}}, 
        'summary' : {'field':'name', 'type':'text'}, 
        'transp' : {'field':'transparent', 'type':'text'}, 
        'uid' : {'field':'id', 'type':'text'}, 
        'url' : {'field':'caldav_url', 'type':'text'}, 
        'recurid' : None, 
#        'attach' : {'field':'attachment_ids', 'sub-field':'datas', 'type':'list'}, 
        'attendee' : {'field':'attendees', 'type':'text'}, 
#        'categories' : {'field':'categ_id', 'sub-field':'name'},
#        'categories' : {'field':None , 'sub-field':'name', 'type':'text'}, # keep none for now
        'comment' : None, 
        'contact' : None, 
        'exdate'  : None, 
        'exrule'  : None, 
        'rstatus' : None, 
        'related' : None, 
        'resources' : None, 
        'rdate' : None, 
        'rrule' : {'field':'rrule', 'type':'text'}, 
        'x-openobject-id' : {'field':'id', 'type':'text'}, 
        'x-openobject-model' : {'value':_name, 'type':'text'}, 
#        'duration' : {'field':'duration'}, 
        'dtend' : {'field':'date_closed', 'type':'datetime'}, 
    }
    
    def _get_location(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for case in self.browse(cr, uid, ids):
            if case.partner_address_id:
                add = case.partner_address_id
                st = add.street and add.street+',\n'  or ''
                st2 = add.street2 and add.street2+',\n'  or ''
                ct = add.city and add.city+',\n'  or ''
                zip = add.zip and add.zip or ''
                country = add.country_id and add.country_id.name+',\n'  or ''
                res[case.id] = st + st2+ ct + country + zip
            else:
                res[case.id] = ''
        return res
    
    def _get_rdates(self, cr, uid, ids, name, arg, context=None):
        res = {}
        context.update({'read':True})
        for case in self.read(cr, uid, ids, ['date', 'rrule'], context=context):
            if case['rrule']:
                rule = case['rrule'].split('\n')[0]
                exdate = case['rrule'].split('\n')[1:]
                event_obj = self.pool.get('caldav.event')
                res[case['id']] = str(event_obj.get_recurrent_dates(str(rule), exdate, case['date']))
        return res
    
    _columns = {
        'class' : fields.selection([('PUBLIC', 'PUBLIC'), ('PRIVATE', 'PRIVATE'), \
                 ('CONFIDENTIAL', 'CONFIDENTIAL')], 'Class'), 
        'location' : fields.function(_get_location, method=True, store = True, string='Location', type='text'), 
        'freebusy' : fields.text('FreeBusy'), 
        'transparent' : fields.selection([('OPAQUE', 'OPAQUE'), ('TRANSPARENT', 'TRANSPARENT')], 'Trensparent'), 
        'caldav_url' : fields.char('Caldav URL', size=34), 
        'rrule' : fields.text('Recurrent Rule'), 
        'rdates' : fields.function(_get_rdates, method=True, string='Recurrent Dates', \
                                   store=True, type='text'), 
       'attendees': fields.many2many('crm.caldav.attendee', 'crm_attendee_rel', 'case_id', 'attendee_id', 'Attendees'), 
    }
    
    _defaults = {
             'caldav_url': lambda *a: 'http://localhost:8080', 
             'class': lambda *a: 'PUBLIC', 
             'transparent': lambda *a: 'OPAQUE', 
        }
     
    def export_cal(self, cr, uid, ids, context={}):
        crm_data = self.read(cr, uid, ids, [])
        ical = vobject.iCalendar()
        event_obj = self.pool.get('caldav.event')
        uid_val = ''
        for crm in crm_data:
            vevent = ical.add('vevent')
            for key, val in self.__attribute__.items():
                if key == 'uid':
                    uid_val += str(crm[val['field']])
                    continue
                if val == None or key == 'rrule':  
                    continue
                if val.has_key('field') and val.has_key('sub-field') and crm[val['field']] and crm[val['field']]:
                    vevent.add(key).value = crm[val['field']][1]
                elif val.has_key('field') and crm[val['field']]:
                    if val['type'] == "text":
                        vevent.add(key).value = str(crm[val['field']])
                    elif val['type'] == 'datetime' and crm[val['field']]:
                        vevent.add(key).value = datetime.strptime(crm[val['field']], "%Y-%m-%d %H:%M:%S")
            if crm[self.__attribute__['rrule']['field']]:
                startdate = datetime.strptime(crm['date'], "%Y-%m-%d %H:%M:%S")
                if not startdate:
                    startdate = datetime.now()
                rset1 = rrulestr(str(crm[event_obj.__attribute__['rrule']['field']]), dtstart=startdate, forceset=True)
                vevent.rruleset = rset1
            vevent.add('uid').value = uid_val
        return ical.serialize()#.replace(vobject.icalendar.CRLF, vobject.icalendar.LF).strip()

    def import_cal(self, cr, uid, ids, data, context={}):
        file_content = base64.decodestring(data['form']['file_path'])
        event_obj = self.pool.get('caldav.event')
        event_obj.__attribute__.update(self.__attribute__)
        event_obj.import_ical(cr, uid, file_content)
        vals = {}
        for map_dict in event_obj.__attribute__:
            map_val = event_obj.ical_get(map_dict, 'value')
            field = event_obj.ical_get(map_dict, 'field')
            field_type = event_obj.ical_get(map_dict, 'type')
            if field and map_val:
                if field_type == 'selection':
                    mapping =event_obj.__attribute__[map_dict].get('mapping', False)
                    if mapping:
                        map_val = mapping[map_val]
                if field_type == 'many2one':
                    # TODO: Map field value to many2one object
                    continue # For now
                vals[field] = map_val
        # TODO: Select proper section
        section_id = self.pool.get('crm.case.section').search(cr, uid, [])[0]
        vals.update({'section_id' : section_id})
        vals.pop('id')
        vals.pop('create_date')
        case_id = self.create(cr, uid, vals)
        return

    def search(self, cr, uid, args, offset=0, limit=None, order=None, 
            context=None, count=False):
        res = super(crm_case, self).search(cr, uid, args, offset, 
                limit, order, context, count)
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        res = super(crm_case, self).write(cr, uid, ids, vals, context=context)
        return res
    
    def browse(self, cr, uid, select, context=None, list_class=None, fields_process={}):
        if not type(select) == list :
            # Called from code
            id = int(str(select).split('-')[0])
            return super(crm_case, self).browse(cr, uid, id, context, list_class, fields_process)
        select = map(lambda x:int(str(x).split('-')[0]), select)
        return super(crm_case, self).browse(cr, uid, select, context, list_class, fields_process)

    def read(self, cr, uid, ids, fields=None, context={}, 
            load='_classic_read'):
        """         logic for recurrent event
         example : 123-20091111170822"""
        if context and context.has_key('read'):
            return super(crm_case, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        if not type(ids) == list :
            # Called from code
            ids = int(str(ids).split('-')[0])
            res = super(crm_case, self).read(cr, uid, ids, fields=fields, context=context, load=load)
            return res
        else:
            ids = map(lambda x:int(str(x).split('-')[0]), ids)
        res = super(crm_case, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        read_ids = ",".join([str(x) for x in ids])
        cr.execute('select id,rrule,rdates from crm_case where id in (%s)' % read_ids)
        rrules = filter(lambda x: not x['rrule']==None, cr.dictfetchall())
        rdates = []
        if not rrules:
            return res
        result =  res + []
        for data in rrules:
            if data['rrule'] and data['rdates']: # delete 2nd condition at last
                rdates = eval(data['rdates'])
            for res_temp in res:
                if res_temp['id'] == data['id']:
                    val = res_temp
                    if rdates:
                        result.remove(val)

            for rdate in rdates:
                import re
                idval = (re.compile('\d')).findall(rdate)
                val['date'] = rdate
                id = str(val['id']).split('-')[0]
                val['id'] = id + '-' + ''.join(idval)
                val1 = val.copy()
                result += [val1]
        return result 
    
    def unlink(self, cr, uid, ids, context=None):
        #TODO: Change RRULE
        for id in ids:
            if len(str(id).split('-')) > 1:
                date_new = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(str(str(id).split('-')[1]), "%Y%m%d%H%M%S"))
                for record in self.read(cr, uid, [str(id).split('-')[0]], ['date', 'rdates', 'rrule']):
                    if record['date'] == date_new:
                        self.write(cr, uid, [int(str(id).split('-')[0])], {'rrule' : record['rrule'] +"\n" + str(date_new)})
            else:
                return super(crm_case, self).unlink(cr, uid, ids)
crm_case()


class ir_attachment(osv.osv):
    _name = 'ir.attachment'
    _inherit = 'ir.attachment'

    def search_count(self, cr, user, args, context=None):
        args1 = []
        for arg in args:
            args1.append(map(lambda x:str(x).split('-')[0], arg))
        return super(ir_attachment, self).search_count(cr, user, args1, context)

ir_attachment()
