# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
#
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

