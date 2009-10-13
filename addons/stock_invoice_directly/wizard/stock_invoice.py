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
import pooler
import netsvc

class invoice_directly(wizard.interface):
    def _test_action(obj, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        pick = pool.get('stock.picking').browse(cr, uid, data['id'], context=context)
        if not pick.invoice_state == '2binvoiced':
            return 'end_final'
        return 'invoice'

    def _open_action(obj, cr, uid, data, context):
        res = {
            'name': 'stock.invoice_onshipping',
            'type': 'ir.actions.wizard',
            'wiz_name': 'stock.invoice_onshipping'
        }
        if data['form'].get('new_picking', False):
            res['context'] = "{'new_picking':%d}" % (data['form']['new_picking'],)
        return res

    end_final = {
        'actions':[],
        'result': {
            'type': 'state',
            'state': 'end',
        }
    }

    choice = {
        'actions':[],
        'result': {
            'type': 'choice',
            'next_state': _test_action,
        }
    }

    call_invoice = {
        'actions':[],
        'result': {
            'type': 'action',
            'action': _open_action,
            'state': 'end'
        }
    }
    def __init__(self, *args):
        service = netsvc.LocalService("wizard.stock.partial_picking")
        service._service.states['split']['result']['state'] = 'test_choice'
        service._service.states['invoice'] = self.call_invoice
        service._service.states['test_choice'] = self.choice
        service._service.states['end_final'] = self.end_final
invoice_directly('stock.picking.invoice.directly')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

