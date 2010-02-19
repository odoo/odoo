# -*- encoding: utf-8 -*-
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
disc_form = """<?xml version="1.0"?>

<form string="Discount Notes :">
    <label colspan="2" string="Reason For Giving Discount" align="0.0"/>
    <newline/>
    <field name="note" nolabel="1"/>
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

disc_fields = {
    'note': {
        'string': 'Discount Notes',
        'type': 'char',
        'size': 128,
        'required': True
    },
}

class discount_wizard(wizard.interface):

    def apply_discount(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        order_ref = pool.get('pos.order')
        order_line_ref = pool.get('pos.order.line')
        for order in order_ref.browse(cr, uid, data['ids'], context=context):
            for line in order.lines :
                company_discount = order.company_id.company_discount
                applied_discount =data['form']['discount']
                if applied_discount == 0.00:
                    notice = 'No Discount'
                elif company_discount >=  applied_discount:
                    notice = 'Minimum Discount'
                else:
                    notice = data['form']['note']
                if self.check_discount(cr, uid, data, context) == 'apply_discount':
                    order_line_ref.write(cr, uid, [line.id],
                            {'discount': data['form']['discount'],
                            'price_ded':line.price_unit*line.qty*(data['form']['discount'] or 0)*0.01 or 0.0,
                            'notice':notice
                            },
                            context=context,)
                else :
                    order_line_ref.write(cr, uid, [line.id],
                            {'discount': data['form']['discount'],
                            'notice': notice,
                            'price_ded':line.price_unit*line.qty*(data['form']['discount'] or 0)*0.01 or 0.0 
                            },
                            context=context,)
        return {}

    def check_discount(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        order_ref = pool.get('pos.order')
        for order in order_ref.browse(cr, uid, data['ids'], context=context):
            company_disc = order.company_id.company_discount
            for line in order.lines :
                prod_disc = data['form']['discount']
                if prod_disc <= company_disc :
                   return 'apply_discount'
                else :
                    return 'disc_discount'

    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': _form,
                'fields': _fields,
                'state': (('end', 'Cancel'),
                          ('check_disc', 'Apply Discount', 'gtk-ok', True)
                         )
            }
        },

        'check_disc': {
            'actions': [],
            'result': {'type':'choice','next_state':check_discount}
        },

        'disc_discount': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': disc_form,
                'fields':disc_fields,
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

