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

import time

def _get_default(obj, cr, uid, data, context=None):
    pool = pooler.get_pool(cr.dbname)
    product = pool.get('product.product').browse(cr, uid, data['id'], context)
    return {'product_id': product.id, 'uom_id':product.uom_id.id, 'qty':1.0}

def make_procurement(obj, cr, uid, data, context=None):
    '''Create procurement'''
    pool = pooler.get_pool(cr.dbname)
    wh = pool.get('stock.warehouse').browse(cr, uid, data['form']['warehouse_id'], context)
    user = pool.get('res.users').browse(cr, uid, uid, context)
    procure_id = pool.get('mrp.procurement').create(cr, uid, {
        'name':'INT:'+str(user.login),
        'date_planned':data['form']['date_planned'],
        'product_id':data['form']['product_id'],
        'product_qty':data['form']['qty'],
        'product_uom':data['form']['uom_id'],
        'location_id':wh.lot_stock_id.id,
        'procure_method':'make_to_order',
    }, context=context)
    wf_service = netsvc.LocalService("workflow")
    wf_service.trg_validate(uid, 'mrp.procurement', procure_id, 'button_confirm', cr)
    return {}


class MakeProcurement(wizard.interface):
    '''Wizard that create a procurement from a product form'''

    done_form = """<?xml version="1.0"?>
<form string="Make Procurement">
    <label string="Your procurement request has been sent !"/>
</form>"""
    procurement_form = """<?xml version="1.0"?>
<form string="Internal Procurement Request">
    <label string="This wizard will planify the procurement for this product. This procurement may generate task, production orders or purchase orders." align="0.0" colspan="4"/>
    <field name="product_id"/>
    <field name="warehouse_id"/>
    <field name="qty"/>
    <field name="uom_id"/>
    <field name="date_planned"/>
</form>"""
    procurement_fields = {
        'qty': {'string': 'Quantity', 'type': 'float', 'digits':(16,2), 'required': True},
        'product_id': {'string': 'product', 'type': 'many2one', 'relation': 'product.product', 'required': True, 'readonly':1},
        'uom_id': {'string': 'Unit of Measure', 'type': 'many2one', 'relation': 'product.uom', 'required':True},
        'warehouse_id': {'string': 'Warehouse', 'type': 'many2one', 'relation':'stock.warehouse', 'required':True},
        'date_planned': {'string': 'Planned Date', 'type': 'date', 'required':True, 'default': lambda *args: time.strftime('%Y-%m-%d')}
    }

    states = {
        'init': {
            'actions': [_get_default],
            'result': {'type': 'form', 'arch': procurement_form, 'fields': procurement_fields,
                'state': [
                    ('end', 'Cancel'),
                    ('create', 'Ask New Products')
                ]
            }
        },
        'done': {
            'actions': [],
            'result': {'type': 'form', 'arch': done_form, 'fields': {},
                'state': [
                    ('end', 'Close'),
                ]
            }
        },
        'create': {
            'actions': [],
            'result': {'type': 'action', 'action': make_procurement, 'state': 'done'}
        }
    }

MakeProcurement('product.product.procurement')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

