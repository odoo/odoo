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
from osv import osv
import pooler
from osv import fields
import time


def _launch_wizard(self, cr, uid, data, context):
    """
    Search for a wizard to launch according to the type.
    If type is manual. just confirm the order.
    """

    order_ref= pooler.get_pool(cr.dbname).get('payment.order')
    order= order_ref.browse(cr,uid,data['id'],context)
    t= order.mode and order.mode.type.code or 'manual'
    if t == 'manual' :
        order_ref.set_done(cr,uid,data['id'],context)
        return {}

    gw= order_ref.get_wizard(t)
    if not gw:
        order_ref.set_done(cr,uid,data['id'],context)
        return {}       

    mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
    act_obj = pooler.get_pool(cr.dbname).get('ir.actions.wizard')
    module, wizard= gw
    result = mod_obj._get_id(cr, uid, module, wizard)
    id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
    result = act_obj.read(cr, uid, [id])[0]
    #result['context'] = str({'fiscalyear': data['form']['fiscalyear']})
    return result


class wizard_pay(wizard.interface):

    states= {'init' : {'actions': [],       
                       'result':{'type':'action',
                                 'action':_launch_wizard,
                                 'state':'end'}
                       }
             }
wizard_pay('pay_payment')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

