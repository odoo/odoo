# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (c) 2008 Sylëam Info Services. (http://www.syleam.fr) All Rights Reserved.
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

import pooler
import wizard
from osv import osv

form_gencod = """<?xml version="1.0"?>
<form string="Scan product">
<label string="Scan Barcode" colspan="4"/>
<field name="gencod" colspan="4" nolabel="1"/>
</form>
"""

fields_gencod = {
    'gencod': {'string': 'Barcode',
               'type': 'char',
               'size': 13,
               'required': True}
}


def _scan(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    result = pool.get('pos.order.line')._scan_product(cr, uid, data['form']['gencod'], 1, data['id'])
    return {'gencod': False}

def _pre_init(self, cr, uid, data, context):
    return {'gencod': False}

class pos_scan_product(wizard.interface):
    states = {
        'init' : {'actions' : [_pre_init],
                'result' : {
                    'type': 'form',
                    'arch': form_gencod,
                    'fields': fields_gencod,
                    'state': [('end','Cancel','gtk-cancel'),
                              ('add', 'Add', 'gtk-ok', True)],
            }
        },
        'add' : {'actions' : [_scan],
                'result' : {
                    'type': 'state',
                    'state': 'init',
                }
        }
    }

pos_scan_product('pos.scan_product')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
