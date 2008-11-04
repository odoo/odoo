# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

import time
import tools
from osv import fields,osv,orm
import os
import mx.DateTime
import base64

#AVAILABLE_STATES = [
#    ('draft','Unreviewed'),
#    ('open','Open'),
#    ('cancel', 'Refuse Bug'),
#    ('done', 'Done'),
#    ('pending','Pending')
#]
class crm_case_category2(osv.osv):
    _name = "crm.case.category2"
    _description = "Category2 of case"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Case Category2 Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
crm_case_category2()

class crm_case_stage(osv.osv):
    _name = "crm.case.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _columns = {
        'name': fields.char('Stage Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Case Section'),
    }
crm_case_stage()

class crm_cases(osv.osv):
    _name = "crm.case"
    _inherit = "crm.case"
    _columns = {
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id)]"),
        'category2_id': fields.many2one('crm.case.category2','Category Name', domain="[('section_id','=',section_id)]"),
        'duration': fields.float('Duration'),
        'note': fields.text('Note'),
        'case_id': fields.many2one('crm.case','Related Case'),
        'partner_name': fields.char('Employee Name', size=64),
        'partner_name2': fields.char('Employee Email', size=64),
        'partner_phone': fields.char('Phone', size=16),
        'partner_mobile': fields.char('Mobile', size=16),
    }
    def onchange_case_id(self, cr, uid, ids, case_id, name, partner_id, context={}):
        if not case_id: return {}
        case = self.browse(cr, uid, case_id, context=context)
        value = {}
        if not name:
            value['name'] = case.name
        if (not partner_id) and case.partner_id:
            value['partner_id'] = case.partner_id.id
            if case.partner_address_id:
                value['partner_address_id'] = case.partner_address_id.id
            if case.email_from:
                value['email_from'] = case.email_from
        return {'value':value}

crm_cases()

class crm_menu_config_wizard(osv.osv_memory):
    _name='crm.menu.config_wizard'
    _columns = {
        'name':fields.char('Name', size=64),
        'meeting' : fields.boolean('Calendar of Meetings', help="Manages the calendar of meetings of the users."),
        'lead' : fields.boolean('Leads', help="Allows you to track and manage leads which are pre-sales requests or contacts, the very first contact with a customer request."),
        'opportunity' : fields.boolean('Business Opportunities', help="Tracks identified business opportunities for your sales pipeline."),
        'jobs' : fields.boolean('Jobs Hiring Process', help="Help you to organise the jobs hiring process: evaluation, meetings, email integration..."),
        'document_ics':fields.boolean('Shared Calendar', help=" Will allow you to synchronise your Open ERP calendars with your phone, outlook, Sunbird, ical, ..."),
        'bugs' : fields.boolean('Bug Tracking', help="Used by companies to track bugs and support requests on softwares"),
        'helpdesk': fields.boolean('Helpdesk', help="Manages an Helpdesk service."),
        'fund' : fields.boolean('Fund Raising Operations', help="This may help associations in their fund raising process and tracking."),
        'claims' : fields.boolean('Claims', help="Manages the supplier and customers complaints."),
        'phonecall' : fields.boolean('Phone Calls', help="Help you to encode the result of a phone call"),
    }
    _defaults = {
        'meeting': lambda *args: True,
        'jobs': lambda *args: True,
        'opportunity': lambda *args: True,
        'phonecall': lambda *args: True,
    }
    def action_create(self, cr, uid, ids, *args):
        modid = self.pool.get('ir.module.module').search(cr, uid, [('name','=','crm_configuration')])
        moddemo = self.pool.get('ir.module.module').browse(cr, uid, modid[0]).demo
        lst= ('data','menu')
        if moddemo:
            lst = ('data','menu','demo')
        res = self.read(cr,uid,ids)[0]
        idref = {}
        for section in ['meeting','lead','opportunity','jobs','bugs','fund','helpdesk','claims','phonecall'] :
            if (not res[section]):
                continue
            for fname in lst:
                file_name = 'crm_'+section+'_'+fname+'.xml'
                try:
                    fp = tools.file_open(os.path.join('crm_configuration',file_name ))
                except IOError, e:
                    fp = None
                if fp:
                    tools.convert_xml_import(cr, 'crm_configuration', fp,  idref, 'init', noupdate=True)
        for name in idref.keys():
            cr.execute('delete from ir_model_data where name=%s and module=%s', (name, 'crm_configuration'))
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }
    def action_cancel(self,cr,uid,ids,conect=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }

crm_menu_config_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

