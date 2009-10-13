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

#
# Order Point Method:
#    - Order if the virtual stock of today is bellow the min of the defined order point
#

import wizard
import threading
import pooler

parameter_form = '''<?xml version="1.0"?>
<form string="Parameters" colspan="4">
    <field name="automatic" />
</form>'''

parameter_fields = {
    'automatic': {'string': 'Automatic orderpoint', 'type': 'boolean', 'help': 'If the stock of a product is under 0, it will act like an orderpoint', 'default': lambda *a: False},
}

def _procure_calculation_orderpoint(self, db_name, uid, data, context):
    db, pool = pooler.get_db_and_pool(db_name)
    cr = db.cursor()
    try:
        proc_obj = pool.get('mrp.procurement')
        automatic = data['form']['automatic']
        proc_obj._procure_orderpoint_confirm(cr, uid, automatic=automatic,\
                use_new_cursor=cr.dbname, context=context)
    finally:
        cr.close()
    return {}

def _procure_calculation(self, cr, uid, data, context):
    threaded_calculation = threading.Thread(target=_procure_calculation_orderpoint, args=(self, cr.dbname, uid, data, context))
    threaded_calculation.start()
    return {}

class procurement_compute(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':parameter_form, 'fields': parameter_fields, 'state':[('end','Cancel'),('compute','Compute Procurements')]}
        },
        'compute': {
            'actions': [_procure_calculation],
            'result': {'type': 'state', 'state':'end'}
        },
    }
procurement_compute('mrp.procurement.orderpoint.compute')



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

