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
import pooler
import time

def _action_open_window(self, cr, uid, data, context):      
    return {
                'view_type': 'form',
                "view_mode": 'tree,form',
                'res_model': 'product.product',
                'type': 'ir.actions.act_window',
                'context':{'location': data['ids'][0],'from_date':data['form']['from_date'],'to_date':data['form']['to_date']},
                'domain':[('type','<>','service')]
     }


class product_by_location(wizard.interface):
    
    form1 = '''<?xml version="1.0"?>
    <form string="View Stock of Products">
        <field name="from_date"/>
        <newline/>
        <field name="to_date"/>
    </form>'''
    
    form1_fields = {
             'from_date': {
                'string': 'From',
                'type': 'date',
        },
             'to_date': {
                'string': 'To',
                'type': 'date',
        },
    }

    states = {
      'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':form1, 'fields':form1_fields, 'state': [ ('open', 'Open Products'),('end', 'Cancel')]}
        },
    'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
    
product_by_location('stock.location.products')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
