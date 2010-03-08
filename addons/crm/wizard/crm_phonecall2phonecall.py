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
        values={}
        values['name']=this.name
        values['user_id']=this.user_id and this.user_id.id
        values['categ_id']=this.category_id and this.category_id.id
        values['section_id']=this.section_id and this.section_id.id or False,
        values['description']=this.notes 
        values['partner_id']=this.partner_id
        values['partner_address_id']=this.address_id.id
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
        'section_id':fields.many2one('crm.case.section','Sales Team'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'address_id': fields.many2one('res.partner.address', 'Partner Contact', domain="[('partner_id','=',partner_id)]"),        
        'notes' : fields.text('Notes'),
    }
    def default_get(self, cr, uid, fields, context=None):
        record_id = context and context.get('record_id', False) or False
        res = super(crm_phonecall2phonecall, self).default_get(cr, uid, fields, context=context)
       
        if record_id:
            phonecall_id = self.pool.get('crm.phonecall').browse(cr, uid, record_id, context=context)
            print ":::::::::",phonecall_id.section_id.id
            res['name']=phonecall_id.name
            res['user_id']=phonecall_id.user_id and phonecall_id.user_id.id
            res['section_id']=phonecall_id.section_id and phonecall_id.section_id.id
            res['notes']=phonecall_id.description and phonecall_id.description
            res['category_id']=phonecall_id.categ_id and phonecall_id.categ_id.id
            res['partner_id']=phonecall_id.partner_id and phonecall_id.partner_id.id
            res['address_id']=phonecall_id.partner_address_id and phonecall_id.partner_address_id.id
             
        return res
crm_phonecall2phonecall()