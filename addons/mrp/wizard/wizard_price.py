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

price_form = '''<?xml version="1.0"?>
<form string="Paid ?">
    <field name="number"/>
</form>'''

price_fields = {
    'number': {'string':'Number of products to produce', 'type':'integer', 'required':True},
}

class wizard_price(wizard.interface):
    states = {
        'init': {
            'actions': [], 
            'result': {'type':'form', 'arch':price_form, 'fields':price_fields, 'state':[('end','Cancel'),('price','Print product price') ]}
        },
        'price': {
            'actions': [],
            'result': {'type':'print', 'report':'product.price', 'state':'end'}
        }
    }
wizard_price('product_price')



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

