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

import wizard

qty1_form = '''<?xml version="1.0"?>
<form string="Price list">
    <field name="price_list" />
    <field name="qty1" colspan="2" />
    <field name="qty2" colspan="2" />
    <field name="qty3" colspan="2" />
    <field name="qty4" colspan="2" />
    <field name="qty5" colspan="2" />

</form>'''
qty1_fields = {
        'price_list' : {'string' : 'PriceList', 'type' : 'many2one', 'relation' : 'product.pricelist', 'required':True },
        'qty1': {'string':'Quantity-1', 'type':'integer', 'default':0},
        'qty2': {'string':'Quantity-2', 'type':'integer', 'default':0},
        'qty3': {'string':'Quantity-3', 'type':'integer', 'default':0},
        'qty4': {'string':'Quantity-4', 'type':'integer', 'default':0},
        'qty5': {'string':'Quantity-5', 'type':'integer', 'default':0},
}


class wizard_qty(wizard.interface):

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':qty1_form, 'fields':qty1_fields, 'state':[('end','Cancel'),('price','Print')]}
        },
        'price': {
            'actions': [],
            'result': {'type':'print', 'report':'product.pricelist', 'state':'end'}
        }

    }
wizard_qty('product.price_list')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

