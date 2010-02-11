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

from osv import fields, osv
from crm import crm
class crm_meeting(osv.osv):
    _name = 'crm.meeting'
    _description = "Meetings"
    _order = "id desc"
    _inherit = ["crm.case", "calendar.event"]

    _columns = { 
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'), 
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.meeting')]", \
            help='Category related to the section.Subdivide the CRM cases \
independently or section-wise.'),            
        'phonecall_id':fields.many2one ('crm.phonecall', 'Phonecall'),        
        'opportunity_id':fields.many2one ('crm.opportunity', 'Opportunity'),       
        'attendee_ids': fields.many2many('calendar.attendee', 'event_attendee_rel', 'event_id', 'attendee_id', 'Attendees'),
    }

crm_meeting()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
