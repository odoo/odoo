# -*- encoding: utf-8 -*-
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
import netsvc
import pooler

cancel_form = """<?xml version="1.0"?>
<form string="Cancel Repair...??">
    <label colspan="4" string="This operation  will  cancel the  Repair process, but  not the  Invoice  or Packing generated.\nDo you want to continue?" />
</form>
"""

cancel_fields = {}

def check_state(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    repair_obj = pool.get('mrp.repair').browse(cr, uid, data['ids'])[0]
    if repair_obj.state == 'draft':
        pool.get('mrp.repair').write(cr,uid,data['ids'],{'state':'cancel'})
        return 'end'
    else:
        return 'display'
        
def _cancel_repair(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    repair_obj = pool.get('mrp.repair').browse(cr, uid, data['ids'])[0]
    pool.get('mrp.repair').write(cr,uid,data['ids'],{'state':'cancel'})
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

