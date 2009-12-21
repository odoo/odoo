# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from service import web_services

def caldevIDs2readIDs(caldev_ID = None):
    if caldev_ID:
        if isinstance(caldev_ID, str):
            return int(caldev_ID.split('-')[0])
        return caldev_ID


class crm_caldav_attendee(osv.osv):
    _name = 'crm.caldav.attendee'
    _description = 'Attendee information'
    _rec_name = 'cutype'

    __attribute__ = {
        'cutype': {'field':'cutype', 'type':'text'}, 
        'member': {'field':'member', 'type':'text'}, 
        'role': {'field':'role', 'type':'selection'}, 
        'partstat': {'field':'partstat', 'type':'text'}, 
        'rsvp': {'field':'rsvp', 'type':'boolean'}, 
        'delegated-to': {'field':'delegated_to', 'type':'char'}, 
        'delegated-from': {'field':'delegated_from', 'type':'char'}, 
        'sent-by': {'field':'sent_by', 'type':'text'}, 
        'cn': {'field':'cn', 'type':'text'}, 
        'dir': {'field':'dir', 'type':'text'}, 
        'language': {'field':'language', 'type':'text'}, 
    }

    _columns = {
            'cutype': fields.selection([('INDIVIDUAL', 'INDIVIDUAL'), ('GROUP', 'GROUP'), \
                                             ('RESOURCE', 'RESOURCE'), ('ROOM', 'ROOM'), \
                                              ('UNKNOWN', 'UNKNOWN') ], 'CUTYPE'), 
            'member': fields.char('Member', size=124), 
            'role': fields.selection([ ('REQ-PARTICIPANT', 'REQ-PARTICIPANT'), \
                                ('CHAIR', 'CHAIR'), ('OPT-PARTICIPANT', 'OPT-PARTICIPANT'), \
                                ('NON-PARTICIPANT', 'NON-PARTICIPANT')], 'ROLE'), 
            'partstat': fields.selection([('NEEDS-ACTION', 'NEEDS-ACTION'), \
                            ('ACCEPTED', 'ACCEPTED'), ('DECLINED', 'DECLINED'), \
                            ('TENTATIVE', 'TENTATIVE'), \
                            ('DELEGATED', 'DELEGATED')], 'PARTSTAT'), 
            'rsvp':  fields.boolean('RSVP'), 
            'delegated_to': fields.char('DELEGATED-TO', size=124), 
            'delegated_from': fields.char('DELEGATED-FROM', size=124), 
            'sent_by': fields.char('SENT-BY', size=124), 
            'cn': fields.char('CN', size=124), 
            'dir': fields.char('DIR', size=124), 
            'language': fields.char('LANGUAGE', size=124), 
                }
    _defaults = {
        'cn':  lambda *x: 'MAILTO:', 
        }
    
crm_caldav_attendee()

class crm_caldav_alarm(osv.osv):
    _name = 'crm.caldav.alarm'
    _description = 'Event alarm information'

    __attribute__ = {
            'action': {'field': 'action', 'type': 'text'}, 
            'description': {'field': 'name', 'type': 'text'}, 
            'summary': {'field': 'description', 'type': 'text'}, 
            'attendee': {'field': 'attendee_ids', 'type': 'text'}, 
            'trigger_related': {'field': 'trigger_related', 'type': 'text'}, 
            'trigger_duration': {'field': 'trigger_duration', 'type': 'text'}, 
            'trigger_occurs': {'field': 'trigger_occurs', 'type': 'text'}, 
            'trigger_interval': {'field': 'trigger_interval', 'type': 'text'}, 
            'duration': {'field': 'duration', 'type': 'text'}, 
            'repeat': {'field': 'repeat', 'type': 'text'}, 
            'attach': {'field': 'attach', 'type': 'text'}, 
    }
     
    _columns = {
            'name': fields.char('Summary', size=124), 
            'action': fields.selection([('AUDIO', 'AUDIO'), ('DISPLAY', 'DISPLAY'), \
                    ('PROCEDURE', 'PROCEDURE'), ('EMAIL', 'EMAIL') ], 'Action', required=True), 
            'description': fields.text('Description'), 
            'attendee_ids': fields.many2many('crm.caldav.attendee', 'alarm_attendee_rel', \
                                          'alarm_id', 'attendee_id', 'Attendees'), 
            'trigger_occurs': fields.selection([('BEFORE', 'BEFORE'), ('AFTER', 'AFTER')], \
                                        'Trigger time', required=True), 
            'trigger_interval': fields.selection([('MINUTES', 'MINUTES'), ('HOURS', 'HOURS'), \
                    ('DAYS', 'DAYS')], 'Trugger duration', required=True), 
            'trigger_duration':  fields.integer('TIme', required=True), 
            'trigger_related':  fields.selection([('start', 'The event starts'), ('end', \
                                           'The event ends')], 'Trigger Occures at', required=True), 
            'duration': fields.integer('Duration'), 
            'repeat': fields.integer('Repeat'), # TODO 
            'attach': fields.binary('Attachment'), 
            'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the event alarm information without removing it."), 
                }

    _defaults = {
        'action':  lambda *x: 'EMAIL', 
        'trigger_interval':  lambda *x: 'MINUTES', 
        'trigger_duration': lambda *x: 5, 
        'trigger_occurs': lambda *x: 'BEFORE', 
        'trigger_related': lambda *x: 'start', 
                 }
    
crm_caldav_alarm()

class ir_attachment(osv.osv):
    _name = 'ir.attachment'
    _inherit = 'ir.attachment'

    def search_count(self, cr, user, args, context=None):
        args1 = []
        for arg in args:
            args1.append(map(lambda x:str(x).split('-')[0], arg))
        return super(ir_attachment, self).search_count(cr, user, args1, context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, 
            context=None, count=False):
        new_args = []
        if len(args) > 1:
            new_args = [args[0]]
            if args[1][0] == 'res_id':
                new_args.append((args[1][0], args[1][1], caldevIDs2readIDs(args[1][2])))
        if new_args:
            args = new_args
        return super(ir_attachment, self).search(cr, uid, args, offset=offset, 
                                                limit=limit, order=order, 
                                                context=context, count=False)
ir_attachment()

class ir_values(osv.osv):
    _inherit = 'ir.values'

    def set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, \
                         meta=False, preserve_user=False, company=False):
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], caldevIDs2readIDs(data[1])))
            else:
                new_model.append(data)
        return super(ir_values, self).set(cr, uid, key, key2, name, new_model, value, \
                                   replace, isobject, meta, preserve_user, company)

    def get(self, cr, uid, key, key2, models, meta=False, context={}, res_id_req=False, \
                    without_user=True, key2_req=True):
        new_model = []
        for data in models:
            if type(data) in (list, tuple):
                new_model.append((data[0], caldevIDs2readIDs(data[1])))
            else:
                new_model.append(data)
        return super(ir_values, self).get(cr, uid, key, key2, new_model, meta, context, \
                                      res_id_req, without_user, key2_req)

ir_values()

class ir_model(osv.osv):

    _inherit = 'ir.model'

    def read(self, cr, uid, ids, fields=None, context={}, 
            load='_classic_read'):
        data = super(ir_model, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        if data:
            for val in data:
                val['id'] = caldevIDs2readIDs(val['id'])
        return data
    
ir_model()

class virtual_report_spool(web_services.report_spool):

    def exp_report(self, db, uid, object, ids, datas=None, context=None):
        if object == 'printscreen.list':
            return super(virtual_report_spool, self).exp_report(db, uid, object, ids, datas, context)
        new_ids = []
        for id in ids:
            new_ids.append(caldevIDs2readIDs(id))
        datas['id'] = caldevIDs2readIDs(datas['id'])
        super(virtual_report_spool, self).exp_report(db, uid, object, new_ids, datas, context)
        return super(virtual_report_spool, self).exp_report(db, uid, object, new_ids, datas, context)

virtual_report_spool()

class virtual_wizard(web_services.wizard):
    def exp_execute(self, db, uid, wiz_id, datas, action='init', context=None):
        if wiz_id not in self.wiz_uid:
            # TODO : To Check why need it
            if wiz_id == 1:
                wiz_name ='base_setup.base_setup'
            if wiz_id == 2:
                wiz_name ='module.upgrade'
            super(virtual_wizard,self).exp_create(db, uid, wiz_name, datas)
        new_ids = []
        if 'id' in datas:
            datas['id'] = caldevIDs2readIDs(datas['id'])
            for id in datas['ids']:
               new_ids.append(caldevIDs2readIDs(id))
            datas['ids'] = new_ids
        res=super(virtual_wizard, self).exp_execute(db, uid, wiz_id, datas, action, context)
        return res

virtual_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: