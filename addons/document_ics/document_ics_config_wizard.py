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

import time
import tools
from osv import fields, osv, orm
import os
import base64
import pooler

SECTION_NAME = {
    'meeting' : 'Meetings',
    'lead':'Leads',
    'opportunity':'Opportunities',
    'jobs':'Jobs',
    'bugs':'Bug Tracking',
    'fund':'Fund Raising',
    'helpdesk':'HelpDesk',
    'claims':'Claims',
    'phonecall':'Phone Calls',
                }

ICS_TAGS = {
        'summary':'Description',
        'uid':'Calendar Code' ,
        'dtstart':'Date' ,
        'dtend':'Deadline' ,
        'url':'Partner Email' ,
        'description':'Your action',
            }

class document_ics_crm_wizard(osv.osv_memory):
    _name='document.ics.crm.wizard'
    _inherit = 'res.config'

    _columns = {
        'name':fields.char('Name', size=64),
        'meeting': fields.boolean('Calendar of Meetings', help="Manages the calendar of meetings of the users."),
        'lead': fields.boolean('Leads', help="Allows you to track and manage leads which are pre-sales requests or contacts, the very first contact with a customer request."),
        'opportunity': fields.boolean('Business Opportunities', help="Tracks identified business opportunities for your sales pipeline."),
        'jobs': fields.boolean('Jobs Hiring Process', help="Helps you to organise the jobs hiring process: evaluation, meetings, email integration..."),
        'document_ics':fields.boolean('Shared Calendar', help=" Will allow you to synchronise your Open ERP calendars with your phone, outlook, Sunbird, ical, ..."),
        'bugs': fields.boolean('Bug Tracking', help="Used by companies to track bugs and support requests on software"),
        'helpdesk': fields.boolean('Helpdesk', help="Manages an Helpdesk service."),
        'fund': fields.boolean('Fund Raising Operations', help="This may help associations in their fund raising process and tracking."),
        'claims': fields.boolean('Claims', help="Manages the supplier and customers claims,including your corrective or preventive actions."),
        'phonecall': fields.boolean('Phone Calls', help="Helps you to encode the result of a phone call or to plan a list of phone calls to process."),
    }
    _defaults = {
        'meeting': lambda *args: True,
        'opportunity': lambda *args: True,
        'phonecall': lambda *args: True,
    }

    def execute(self, cr, uid, ids, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Document CRM wizard’s IDs
            @param context: A standard dictionary for contextual values """

        data = self.read(cr, uid, ids, [], context=context)[0]
        dir_obj = self.pool.get('document.directory')
        dir_cont_obj = self.pool.get('document.directory.content')
        dir_id = dir_obj.search(cr, uid, [('name', '=', 'Calendars')])
        if dir_id:
            dir_id = dir_id[0]
        else:
            dir_id = dir_obj.create(cr, uid, {'name': 'Calendars' ,'user_id' : uid, 'type': 'directory'})
        for section in ['meeting', 'lead', 'opportunity', 'jobs', 'bugs', 'fund', \
                            'helpdesk', 'claims', 'phonecall']:
            if data[section]:
                section_id=self.pool.get('crm.case.section').search(cr, uid, \
                            [('name', '=', SECTION_NAME[section])])
                if section_id:
                    object_id=self.pool.get('ir.model').search(cr, uid, [('name', '=', 'Case')])[0]

                    vals_cont = {
                          'name': SECTION_NAME[section],
                          'sequence': 1,
                          'directory_id': dir_id,
                          'suffix': section,
                          'extension': '.ics',
                          'ics_object_id': object_id,
                          'ics_domain': [('section_id', '=', section_id[0])],
                          'include_name' : False
                        }

                    content_id = dir_cont_obj.create(cr, uid, vals_cont)

                    ics_obj=self.pool.get('document.directory.ics.fields')
                    for tag in ['description', 'url', 'summary', 'dtstart', 'dtend', 'uid']:
                        field_id =  self.pool.get('ir.model.fields').search(cr, uid,\
                                    [('model_id.name', '=', 'Case'),\
                                    ('field_description', '=', ICS_TAGS[tag])])[0]
                        vals_ics = {
                            'field_id':  field_id ,
                            'name':  tag ,
                            'content_id': content_id ,
                            }
                        ics_obj.create(cr, uid, vals_ics)

document_ics_crm_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
