# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wizard
import netsvc
import ir
import pooler

set_to_zero_form = """<?xml version="1.0"?>
<form string="Reset cashbox">
    <label string="Are you sure you want to reset this cashbox ?"/>
</form>"""



confirm_setting_zero_fields = {}

def _set_to_zero(self,cr,uid,data,context):
    pool= pooler.get_pool(cr.dbname)
    cashmove_ref = pool.get('lunch.cashmove')
    cr.execute("select user_cashmove, box,sum(amount) from lunch_cashmove where active= 't' and box in (%s) group by user_cashmove, box"%','.join(map(str,data['ids'])))
    res= cr.fetchall()
    cr.execute("update lunch_cashmove set active = 'f' where active= 't' and box in (%s)"%','.join(map(str,data['ids'])))
##    to_unactive= {}.fromkeys([r[0] for r in cr.fetchall]).keys()
##    print to_unactive
##    cashmove_ref.write(cr,uid,to_unactive,{'active':False})            
##    
    for (user_id,box_id,amount) in res:
        cashmove_ref.create(cr,uid,{'name': 'Summary for user'+ str(user_id),
                        'amount': amount,
                        'user_cashmove': user_id,
                        'box': box_id,
                        'active': True,
                        })
    return {}


class cashbox_set_to_zero(wizard.interface):

    states = {
            
        'init': {
                        'action':[],
                        'result':{'type' : 'form',
                          'arch' : set_to_zero_form,
              'fields' : confirm_setting_zero_fields,
                          'state' : [('end', 'Cancel'),('zero', 'Set to Zero') ]},
    
        },
        'zero' : {
            'actions' : [_set_to_zero],
            'result' : {'type' : 'state', 'state' : 'end'}
        },
    }
    
cashbox_set_to_zero('lunch.cashbox.clean')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

