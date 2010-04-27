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
import datetime

from osv import fields, osv
from tools.translate import _

class account_use_model(osv.osv_memory):

    _name = 'account.use.model'
    _description = 'Use model'
    _columns = {
        'model': fields.many2many('account.model', 'account_use_model_relation','account_id','model_id','Account Model'),
        }

    def create_entries(self, cr, uid, ids, context=None):
        account_model_obj = self.pool.get('account.model')
        account_period_obj = self.pool.get('account.period')
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}

        data =  self.read(cr, uid, ids,context=context)[0]
        record_id = context and context.get('model_line', False) or False
        if record_id:
            data_model = account_model_obj.browse(cr,uid,data['model'])
        else:
            data_model = account_model_obj.browse(cr,uid,context['active_ids'])
        move_ids = []
        for model in data_model:
                period_id = account_period_obj.find(cr, uid, context=context)
                if not period_id:
                    raise osv.except_osv(_('No period found !'), _('Unable to find a valid period !'))
                period_id = period_id[0]
                move_id = account_move_obj.create(cr, uid, {
                    'ref': model.ref,
                    'period_id': period_id,
                    'journal_id': model.journal_id.id,
                })
                move_ids.append(move_id)
                for line in model.lines_id:
                    val = {
                        'move_id': move_id,
                        'journal_id': model.journal_id.id,
                        'period_id': period_id
                    }
                    val.update({
                        'name': line.name,
                        'quantity': line.quantity,
                        'debit': line.debit,
                        'credit': line.credit,
                        'account_id': line.account_id.id,
                        'move_id': move_id,
                        'ref': line.ref,
                        'partner_id': line.partner_id.id,
                        'date': time.strftime('%Y-%m-%d'),
                        'date_maturity': time.strftime('%Y-%m-%d')
                    })
                    c = context.copy()
                    c.update({'journal_id': model.journal_id.id,'period_id': period_id})
                    id_line = account_move_line_obj.create(cr, uid, val, context=c)
        context.update({'move_ids':move_ids})
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','view_account_use_model_open_entry')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
            'name': _('Use Model'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.use.model',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            }

    def open_moves(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','view_move_form')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str,context['move_ids']))+"])]",
            'name': 'Entries',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [(False,'tree'),(resource_id,'form')],
            'type': 'ir.actions.act_window',
        }

account_use_model()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

