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

import wizard
import netsvc
import pooler
import time
from tools.translate import _
import tools
from osv import fields, osv


class account_move_journal(osv.osv_memory):
    
    def _get_period(self, cr, uid, context={}):
        """Return  default account period value""" 
        
        ids = self.pool.get('account.period').find(cr, uid, context=context)
        period_id = False
        if len(ids):
            period_id = ids[0]
        return period_id
    
    def _action_open_window(self, cr, uid, ids, context={}):
        """
        cr is the current row, from the database cursor,
        uid is the current user’s ID for security checks,
        ID is the account move journal’s ID or list of IDs if we want more than one
        This function Open action move line window on given period and  Journal/Payment Mode
        """
        for form in  self.read(cr, uid, ids,['journal_id', 'period_id']):
            cr.execute('select id,name from ir_ui_view where model=%s and type=%s', ('account.move.line', 'form' ))
            view_res = cr.fetchone()
            jp = self.pool.get('account.journal.period')
            ids = jp.search(cr, uid, [('journal_id','=',form['journal_id']), ('period_id','=',form['period_id'])])
            
            if not len(ids):
                print "ids",ids
                name = self.pool.get('account.journal').read(cr, uid, [form['journal_id']])[0]['name']
                state = self.pool.get('account.period').read(cr, uid, [form['period_id']])[0]['state']
                if state == 'done':
                    raise osv.except_osv(_('UserError'), _('This period is already closed !'))
                company = self.pool.get('account.period').read(cr, uid, [form['period_id']])[0]['company_id'][0]
                jp.create(cr, uid, {'name':name, 'period_id': form['period_id'], 'journal_id':form['journal_id'], 'company_id':company})
            ids = jp.search(cr, uid, [('journal_id','=',form['journal_id']), ('period_id','=',form['period_id'])])
            print "jp",ids
            jp = jp.browse(cr, uid, ids, context=context)[0]
            name = (jp.journal_id.code or '') + ':' + (jp.period_id.code or '')
            mod_obj = self.pool.get('ir.model.data')
            result = mod_obj._get_id(cr, uid, 'account', 'view_account_move_line_filter')
            id = mod_obj.read(cr, uid, result, ['res_id']) 
            return {
                'domain': "[('journal_id','=',%d), ('period_id','=',%d)]" % (form['journal_id'],form['period_id']),
                'name': name,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move.line',
                'view_id': view_res,
                'context': "{'journal_id':%d, 'period_id':%d}" % (form['journal_id'],form['period_id']),
                'type': 'ir.actions.act_window',
                'search_view_id': id['res_id']        
                }
            
    _name = "account.move.journal"
    _description = "Move journal"
    
    _columns = {
                'journal_id':fields.many2one('account.journal',  'Journal/Payment Mode', required=True),
                'period_id':fields.many2one('account.period', 'Period', required=True),
                }

    _defaults = {
                'period_id':_get_period
                }
    
account_move_journal()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

