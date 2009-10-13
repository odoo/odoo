# -*- coding: utf-8 -*-
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
import wizard
import time
import datetime
import pooler
from tools.translate import _

model_form = """<?xml version="1.0"?>
<form string="Select Message">
    <field name="model"/>
</form>"""

model_fields = {
    'model': {'string': 'Account Model', 'type': 'many2many', 'relation': 'account.model', 'required': True},
   }

form = """<?xml version="1.0"?>
<form string="Use Model">
    <label string="Move Lines Created."/>
</form>
"""
fields = {
          }
def _create_entries(self, cr, uid, data, context):
    pool_obj = pooler.get_pool(cr.dbname)
    if data['model']=='ir.ui.menu' or data['model']=='account.move.line':
        model_ids = data['form']['model'][0][2]
        data_model = pool_obj.get('account.model').browse(cr,uid,model_ids)
    else:
        data_model = pool_obj.get('account.model').browse(cr,uid,data['ids'])
    move_ids = []
    for model in data_model:

            period_id = pool_obj.get('account.period').find(cr,uid, context=context)
            if not period_id:
                raise wizard.except_wizard(_('No period found !'), _('Unable to find a valid period !'))
            period_id = period_id[0]
            move_id = pool_obj.get('account.move').create(cr, uid, {
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
                id_line = pool_obj.get('account.move.line').create(cr, uid, val, context=c)
    data['form']['move_ids']=move_ids
    return data['form']

class use_model(wizard.interface):

    def _open_moves(self, cr, uid, data, context):
        pool_obj = pooler.get_pool(cr.dbname)
        model_data_ids = pool_obj.get('ir.model.data').search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_move_form')])
        resource_id = pool_obj.get('ir.model.data').read(cr,uid,model_data_ids,fields=['res_id'])[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str,data['form']['move_ids']))+"])]",
            'name': 'Entries',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [(False,'tree'),(resource_id,'form')],
            'type': 'ir.actions.act_window'
        }

    def _check(self, cr, uid, data, context):
        if data['model']=='ir.ui.menu' or data['model']=='account.move.line':
             return 'init_form'
        return 'create'

    states = {
        'init': {
            'actions': [],
            'result': {'type':'choice','next_state':_check}
        },
        'init_form': {
            'actions': [],
            'result': {'type':'form', 'arch':model_form, 'fields':model_fields, 'state':[('end','Cancel'),('create','Create Entries')]},
        },
        'create': {
            'actions': [_create_entries],
            'result': {'type': 'form','arch':form, 'fields':fields, 'state':[('end','Ok'),('open_move','Open')]},
        },
        'open_move': {
            'actions': [],
            'result': {'type':'action', 'action':_open_moves, 'state':'end'}
            }
    }

use_model("account_use_models")# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

