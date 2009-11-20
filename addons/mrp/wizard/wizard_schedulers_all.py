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
import threading
import pooler

parameter_form = '''<?xml version="1.0"?>
<form string="Scheduler Parameters" colspan="4">
    <field name="automatic" />
</form>'''

parameter_fields = {
    'automatic': {'string': 'Automatic orderpoint', 'type': 'boolean', 'help': 'Triggers an automatic procurement for all products that have a virtual stock under 0. You should probably not use this option, we suggest using a MTO configuration on products.', 'default': lambda *a: False},
}

def _procure_calculation_all(self, db_name, uid, data, context):
    db, pool = pooler.get_db_and_pool(db_name)
    cr = db.cursor()
    proc_obj = pool.get('mrp.procurement')
    automatic = data['form']['automatic']
    proc_obj.run_scheduler(cr, uid, automatic=automatic, use_new_cursor=cr.dbname,\
            context=context)
    cr.close()
    return {}

def _procure_calculation(self, cr, uid, data, context):
    threaded_calculation = threading.Thread(target=_procure_calculation_all, args=(self, cr.dbname, uid, data, context))
    threaded_calculation.start()
    return {}

class procurement_compute(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':parameter_form, 'fields': parameter_fields, 'state':[('end','Cancel'),('compute','Compute Procurements') ]}
        },
        'compute': {
            'actions': [_procure_calculation],
            'result': {'type': 'state', 'state':'end'}
        },
    }
procurement_compute('mrp.procurement.compute.all')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

