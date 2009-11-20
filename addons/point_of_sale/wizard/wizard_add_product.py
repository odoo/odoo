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

import pooler
import wizard


_form = """<?xml version="1.0"?>
<form string="Add product :">
<field name="product"/>
<field name="quantity"/>
</form>
"""
_fields = {
    'product': {
        'string': 'Product',
        'type': 'many2one',
        'relation': 'product.product',
        'required': True,
        'default': False
    },

    'quantity': {
        'string': 'Quantity',
        'type': 'integer',
        'required': True,
        'default': 1},
    }


def _add(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    order_obj.add_product(cr, uid, data['id'], data['form']['product'],
                            data['form']['quantity'], context=context)

    return {}


def _pre_init(self, cr, uid, data, context):
    return {'product': False, 'quantity': 1}


class add_product(wizard.interface):

    states = {
        'init': {
            'actions': [_pre_init],
            'result': {
                'type': 'form',
                'arch': _form,
                'fields': _fields,
                'state': [('end', 'Cancel'), ('add', '_Add product', 'gtk-ok', True)
                ]
            }
        },
        'add': {
            'actions': [_add],
            'result': {
                'type': 'state',
                'state': 'init',
            }
        },
    }

add_product('pos.add_product')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

