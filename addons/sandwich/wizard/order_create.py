# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: makesale.py 1183 2005-08-23 07:43:32Z pinky $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler

sale_form = """<?xml version="1.0"?>
<form string="Make an order">
    <field name="name" required="True" />
    <field name="partner_id" required="True" />
</form>"""

sale_fields = {
    'name' : {'string' : 'Order name', 'type': 'char'},
    'partner_id' : {'string':'Suplier', 'relation':'res.partner', 'type':'many2one'},
}

class make_sale(wizard.interface):
    def _makeOrder(self, cr, uid, data, context):
        order = pooler.get_pool(cr.dbname).get('sandwich.order')
        line = pooler.get_pool(cr.dbname).get('sandwich.order.line')
        oid = order.create(cr, uid, {
            'name': data['form']['name'],
            'partner': data['form']['partner_id'],
        })
        name=data['form']['name']
        cr.execute('update sandwich_order_line set order_id=%d where order_id is null', (oid,))
        value = {
            'domain': "[('id','in',["+str(oid)+"])]",
            'name': "Create Sandwich Orders:"+name,
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'sandwich.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'res_id': oid
        }
        return value

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form', 'arch' : sale_form, 'fields' : sale_fields, 'state' : [('end', 'Cancel'),('order', 'Make an order')]}
        },
        'order' : {
            'actions': [],
            'result': {'type': 'action', 'action': _makeOrder, 'state':'end'},
        }
    }
make_sale('sandwich.order_create')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

