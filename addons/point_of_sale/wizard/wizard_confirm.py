# -*- encoding: utf-8 -*-
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
import netsvc
import pooler
import time

_form = """<?xml version="1.0"?>
<form string="Open Statements">
     <label string="Are you sure you want to close your sales ?" colspan="2"/>
</form>
"""
_fields = {}

def _confirm(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    company_id=pool.get('res.users').browse(cr,uid,uid).company_id
    order_obj = pool.get('pos.order')
    for order_id in order_obj.browse(cr, uid, data['ids'], context=context):
        if  order_id.state =='paid':
            order_obj.write(cr,uid,[order_id.id],{'journal_entry':True})
            order_obj.create_account_move(cr, uid, [order_id.id], context=context)

    wf_service = netsvc.LocalService("workflow")
    for i in data['ids']:
        wf_service.trg_validate(uid, 'pos.order', i, 'done', cr)
    return {}

def _get_state(self, cr, uid, data, context):
    action = 'invoice'
    return action
class pos_confirm(wizard.interface):

 states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': _form,
                'fields': _fields,
                'state': (('end', 'No','gtk-cancel'),
                          ('open', 'Yes', 'gtk-ok', True)
                         )
            }
        },
        'open': {
            'actions': [_confirm],
            'result': {
                       'type': 'state',
                       'state':'end'}
        },
    }

pos_confirm('pos.confirm')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

