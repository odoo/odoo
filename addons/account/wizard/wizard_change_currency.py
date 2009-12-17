#!/usr/bin/env python
# -*- encoding: utf-8 -*-
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
import pooler

class wizard_change_currency(wizard.interface):
    '''
    OpenERP Wizard
    '''
    form = '''<?xml version="1.0"?>
    <form string="Invoice Currency">
        <field name="currency_id"/>
    </form>'''
    
    message = '''<?xml version="1.0"?>
    <form string="Invoice Currency">
        <label string="You can not change currency for Open Invoice !"/>
    </form>'''
    
    fields = {
        'currency_id': {'string': 'New Currency', 'type': 'many2one', 'relation': 'res.currency', 'required':True},
    }

    def _get_defaults(self, cr, user, data, context):
        #TODO : initlize required data
        
        return data['form'] 

    def _change_currency(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        
        inv_obj = pool.get('account.invoice')
        inv_line_obj = pool.get('account.invoice.line')
        curr_obj = pool.get('res.currency')
        
        invoice_ids = data['ids']
        new_currency = data['form']['currency_id']

        for invoice in inv_obj.browse(cr, uid, invoice_ids, context=context):
            if invoice.currency_id.id == new_currency:
                continue
            
            for line in invoice.invoice_line:
                rate = curr_obj.browse(cr, uid, new_currency).rate
                new_price = 0
                if invoice.company_id.currency_id.id == invoice.currency_id.id:
                    new_price = line.price_unit * rate
                    
                if invoice.company_id.currency_id.id != invoice.currency_id.id and invoice.company_id.currency_id.id == new_currency:
                    old_rate = invoice.currency_id.rate
                    new_price = line.price_unit / old_rate
                    
                if invoice.company_id.currency_id.id != invoice.currency_id.id and invoice.company_id.currency_id.id != new_currency:
                    old_rate = invoice.currency_id.rate
                    new_price = (line.price_unit / old_rate ) * rate
                
                inv_line_obj.write(cr, uid, [line.id], {'price_unit':new_price})
            inv_obj.write(cr, uid, [invoice.id], {'currency_id':new_currency})
        return {}

    def _check_what_next(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        inv_obj = pool.get('account.invoice')
        if inv_obj.browse(cr, uid, data['id']).state != 'draft':
            return 'message'
            
        return 'change'
        
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'choice', 'next_state': _check_what_next},
        },
        'change': {
            'actions': [],
            'result': {'type': 'form', 'arch': form, 'fields': fields, 'state': (('end', 'Cancel'), ('next', 'Change Currency'))},
        },
        'next': {
            'actions': [_change_currency],
            'result': {'type': 'state', 'state': 'end'},
        },
        'message': {
            'actions': [],
            'result': {'type': 'form', 'arch': message, 'fields': {}, 'state': [('end', 'Ok')]},
        },
    }
wizard_change_currency('account.invoice.currency_change')
