# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import wizard
import pooler

#
# This class fill in the order with kind of automatically generated order lines, based on the last order for a user concerning a type of product
#
class sandwich_order_wizard(wizard.interface):

    def _sandwich_order_wizard_order(self, cr, uid, data, context):
        if not len(data['ids']):
            return {}
        cr.execute('update sandwich_order_line set order_id=%d where order_id is null', (data['ids'][0],))
        for order in pooler.get_pool(cr.dbname).get('sandwich.order').browse(cr, uid, data['ids']):
            for user_id in data['form']['user_id'][0][2]:
                for producttype in data['form']['product_type_id'][0][2]:
                    if not pooler.get_pool(cr.dbname).get('sandwich.order.line').search(cr, uid, [('user_id','=',user_id),('product_type_id','=',producttype),('order_id','=',order.id)]):
                        vals = {
                            'user_id': user_id,
                            'order_id': order.id,
                            'date': order.date,
                            'product_type_id': producttype
                        }
                        vals.update( pooler.get_pool(cr.dbname).get('sandwich.order.line').onchange_user_id(cr, uid, uid, user_id, producttype)['value'] )
                        pooler.get_pool(cr.dbname).get('sandwich.order.line').create(cr, uid, vals)
        return {}

    _sandwich_order_wizard_form =  '''<?xml version="1.0"?>
        <form string="Complete order">
        <separator string="Set orders for the day" colspan="4"/>
            <field name="user_id"/>
            <field name="product_type_id"/>
        </form> '''
    
    _sandwich_order_wizard_fields = {
        'user_id': {'string': 'User', 'type': 'many2many','relation':'res.users'},
        'product_type_id': {'string': 'Product', 'type': 'many2many', 'relation':'sandwich.product.type'},
    }

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_sandwich_order_wizard_form, 'fields':_sandwich_order_wizard_fields,  'state':[('end','Cancel'),('complete','Complete order')]}
        },
        'complete': {
            'actions': [_sandwich_order_wizard_order],
            'result': {'type': 'state', 'state': 'end'}
        }
    }

sandwich_order_wizard('sandwich.order.wizard')

#
# This class send a request message to users who don't have their order filled in for this day
#
class sandwich_order_recall_wizard(wizard.interface):
    def _sandwich_order_recall_wizard_send(self, cr, uid, data, context):
        for user_id in data['form']['user_id'][0][2]:
            if not pooler.get_pool(cr.dbname).get('sandwich.order.line').search(cr, uid, [('user_id','=',user_id),('order_id','=',data['id'])]):
                request = pooler.get_pool(cr.dbname).get('res.request')
                request.create(cr, uid, {
                    'name' : "Please order your lunch of the day",
                    'priority' : '0',
                    'state' : 'active',
                    'body' : """Hello,

It seems like you have forgotten to order your sandwich (or meal).
As it will be ordered soon, it seems to be a rather nice idea to complete your
order for today ASAP. If you do not, you'll probably get the same meal as yesterday...

Thanks,

-- 
Tiny ERP
""",
                    'act_from' : uid,
                    'act_to' : user_id,
                })
        return {}
        
    _sandwich_order_recall_wizard_form = '''<?xml version="1.0"?>
        <form string="Recall orders to users">
            <separator string="List of user to remind the order" colspan="4"/>
            <field name="user_id" colspan="4"/>
        </form>'''
        
    _sandwich_order_recall_wizard_fields = {
        'user_id': {'string': 'Baaaad users !', 'type': 'many2many', 'relation': 'res.users'},
    }
    
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type': 'form', 'arch': _sandwich_order_recall_wizard_form, 'fields': _sandwich_order_recall_wizard_fields, 'state': [('end','Cancel'),('send','Send')]},
        },
        'send' : {
            'actions' : [_sandwich_order_recall_wizard_send],
            'result' : {'type': 'state', 'state': 'end'},
        }
    }
    
sandwich_order_recall_wizard('sandwich.order.recall.wizard')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

