# -*- encoding: utf-8 -*-
############################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2008-2009 AJM Technologies S.A. (<http://www.ajm.lu). All Rights Reserved
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
############################################################################################
############################################################################################

from osv import osv, fields
import netsvc
import time
import tools
import mx.DateTime
from tools import config
from tools.translate import _
import tools

class crm_phonecall2phonecall(osv.osv_memory):
    _name = 'crm.phonecall2phonecall'
    _description = 'Phonecall To Phonecall'

    def action_cancel(self, cr, uid, ids, context=None):
        return {'type':'ir.actions.act_window_close'}

    def action_apply(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids)[0]

        record_id = context and context.get('record_id', False) or False
        print ">>>>>>>>>>",record_id
        values={}
        values['name']=this.name
        values['user_id']=this.user_id and this.user_id.id
        values['category_id']=this.category_id and this.category_id.id
        values['section_id']=this.section_id and this.section_id.id or False,
        values['description']=this.notes 
        phonecall_proxy = self.pool.get('crm.phonecall')
        phonecall_id = phonecall_proxy.create(cr, uid, values, context=context)  
        value = {            
            'name': _('Phone Call'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.phonecall',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'res_id': phonecall_id
            }
        return value

    _columns = {
        'name' : fields.char('Name', size=64, required=True, select=1),
        'user_id' : fields.many2one('res.users',"Assign To"),
        'deadline': fields.datetime('Deadline', readonly=True),
        'category_id' : fields.many2one('crm.case.categ','Category',domain="[('object_id.model', '=', ''crm.phonecall')]"),
        'section_id':fields.many2one('crm.case.section','Section Id'),
        'notes' : fields.text('Notes'),
    }
crm_phonecall2phonecall()