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


import pooler

import wizard


_form = """<?xml version="1.0"?>
<form string="Discount :">
    <field name="discount"/>
</form>
"""

_fields = {
    'discount': {
        'string': 'Discount percentage',
        'type': 'float',
        'required': True,
        'default': lambda *args: 5
    },
}


def apply_discount(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_ref = pool.get('pos.order')
    order_line_ref = pool.get('pos.order.line')
    for order in order_ref.browse(cr, uid, data['ids'], context=context):
        order_line_ref.write(cr, uid, [line.id for line in order.lines],
                            {'discount': data['form']['discount']},
                            context=context,)
    return {}


class discount_wizard(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': _form,
                'fields': _fields,
                'state': (('end', 'Cancel'),
                          ('apply_discount', 'Apply Discount', 'gtk-ok', True)
                         )
            }
        },
        'apply_discount': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': apply_discount,
                'state': "end",
            }
        },
    }

discount_wizard('pos.discount')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

