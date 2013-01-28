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

from openerp.osv import fields, osv
from openerp.tools.translate import _

import time

class crm_phonecall2phonecall(osv.osv_memory):
    _name = 'crm.phonecall2phonecall'
    _description = 'Phonecall To Phonecall'

    _columns = {
        'name' : fields.char('Call summary', size=64, required=True, select=1),
        'user_id' : fields.many2one('res.users',"Assign To"),
        'contact_name':fields.char('Contact', size=64),
        'phone':fields.char('Phone', size=64),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                domain="['|',('section_id','=',False),('section_id','=',section_id),\
                ('object_id.model', '=', 'crm.phonecall')]"), 
        'date': fields.datetime('Date'),
        'section_id':fields.many2one('crm.case.section','Sales Team'),
        'action': fields.selection([('schedule','Schedule a call'), ('log','Log a call')], 'Action', required=True),
        'partner_id' : fields.many2one('res.partner', "Partner"),
        'note':fields.text('Note')
    }


    def action_cancel(self, cr, uid, ids, context=None):
        """
        Closes Phonecall to Phonecall form
        """
        return {'type':'ir.actions.act_window_close'}

    def action_schedule(self, cr, uid, ids, context=None):
        value = {}
        if context is None:
            context = {}
        phonecall = self.pool.get('crm.phonecall')
        phonecall_ids = context and context.get('active_ids') or []
        for this in self.browse(cr, uid, ids, context=context):
            phocall_ids = phonecall.schedule_another_phonecall(cr, uid, phonecall_ids, this.date, this.name, \
                    this.user_id and this.user_id.id or False, \
                    this.section_id and this.section_id.id or False, \
                    this.categ_id and this.categ_id.id or False, \
                    action=this.action, context=context)

        return phonecall.redirect_phonecall_view(cr, uid, phocall_ids[phonecall_ids[0]], context=context)
    
    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        
        """
        res = super(crm_phonecall2phonecall, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        res.update({'action': 'schedule', 'date': time.strftime('%Y-%m-%d %H:%M:%S')})
        if record_id:
            phonecall = self.pool.get('crm.phonecall').browse(cr, uid, record_id, context=context)

            categ_id = False
            data_obj = self.pool.get('ir.model.data')
            res_id = data_obj._get_id(cr, uid, 'crm', 'categ_phone2')
            if res_id:
                categ_id = data_obj.browse(cr, uid, res_id, context=context).res_id

            if 'name' in fields:
                res.update({'name': phonecall.name})
            if 'user_id' in fields:
                res.update({'user_id': phonecall.user_id and phonecall.user_id.id or False})
            if 'date' in fields:
                res.update({'date': False})
            if 'section_id' in fields:
                res.update({'section_id': phonecall.section_id and phonecall.section_id.id or False})
            if 'categ_id' in fields:
                res.update({'categ_id': categ_id})
            if 'partner_id' in fields:
                res.update({'partner_id': phonecall.partner_id and phonecall.partner_id.id or False})
        return res

crm_phonecall2phonecall()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
