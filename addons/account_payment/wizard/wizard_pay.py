##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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
