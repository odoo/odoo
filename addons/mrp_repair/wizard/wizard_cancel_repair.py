# -*- coding: utf-8 -*-
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
import pooler

cancel_form = """<?xml version="1.0"?>
<form string="Cancel Repair...??">
    <label colspan="4" string="This operation  will  cancel the  Repair process, but  will not cancel it's Invoice.\nDo you want to continue?" />
</form>
"""

cancel_fields = {}

def check_state(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    repair_obj = pool.get('mrp.repair').browse(cr, uid, data['ids'])[0]
    if repair_obj.invoice_id:
        return 'display'
    else:
        pool.get('mrp.repair').write(cr,uid,data['ids'],{'state':'cancel'})
        return 'end'
        
        
def _cancel_repair(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    repair_obj = pool.get('mrp.repair').browse(cr, uid, data['ids'])
    pool.get('mrp.repair').write(cr,uid,data['ids'],{'state':'cancel'})
    mrp_line_obj = pool.get('mrp.repair.line')
    for line in repair_obj:
        mrp_line_obj.write(cr, uid, [l.id for l in line.operations], {'state': 'cancel'})
    return {}

class repair_cancel(wizard.interface):
    states = {
       'init' : {
            'actions' : [],
            'result' : {'type' : 'choice', 'next_state' : check_state}
        },

        'display' : {
            'actions' : [],
            'result' : {'type' : 'form',
                    'arch' : cancel_form,
                    'fields' : cancel_fields,
                    'state' : [('end', 'No'),('yes', 'Yes') ]}
        },
        'yes' : {
            'actions' : [],
            'result' : {'type' : 'action',
                    'action' : _cancel_repair,
                    'state' : 'end'}
        },
         'end' : {
            'actions' : [],
            'result': {'type': 'state', 'state': 'end'},
        },
    }
repair_cancel("mrp.repair.cancel")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

