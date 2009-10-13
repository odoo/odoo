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


#import time
#import netsvc
#from tools.misc import UpdateableStr
#import pooler
import wizard
import pooler


warning_form = '''<?xml version="1.0"?>
<form string="Refund ">
<separator string="Refund order :" colspan="4"/>
<newline/>
<field name="date_validity"/>
</form>
'''

warning_fields = {
    'date_validity': {'string': 'Validity Date', 'type': 'date'}
}


def _get_date(self, cr, uid, data, context):
    order_ref = pooler.get_pool(cr.dbname).get('pos.order')
    order = order_ref.browse(cr, uid, data['id'], context)
    return {'date_validity': order.date_validity}


def _refunding(self, cr, uid, data, context):
    order_ref = pooler.get_pool(cr.dbname).get('pos.order')
    clone_list = order_ref.refund(cr, uid, data['ids'], context)

    if data['form']['date_validity']:
        order_ref.write(cr, uid, clone_list, {
            'date_validity': data['form']['date_validity']
            })

    return {
        'domain': "[('id','in',["+','.join(map(str, clone_list))+"])]",
        'name': 'Refunded Orders',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'pos.order',
        'view_id': False,
        #'context': "{'journal_id':%d}" % (form['journal_id'],),
        'type': 'ir.actions.act_window'
    }


class refund_order(wizard.interface):
    states = {
        'init': {
            'actions': [_get_date],
            'result': {
                'type': 'form',
                'arch': warning_form,
                'fields': warning_fields,
                'state': [('end', 'Cancel', 'gtk-no'), ('refund_n_quit', 'Ok', 'gtk-yes')]
            }
        },
        'refund_n_quit': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _refunding,
                'state': 'end'
            }
        },
    }

refund_order('pos.refund_order')

