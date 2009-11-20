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
import netsvc

invoice_form = '''<?xml version="1.0"?>
<form title="Paid ?">
    <field name="amount"/>
    <field name="objects"/>
    <field name="amount_topay"/>
    <field name="amount_paid"/>
    <!--field name= "tax_applied"/>-->
    <newline/>
    <field name="ach_uid" colspan="3"/>
    <field name="number" colspan="3"/>
    <field label="Let this invoice's number "/>
</form>'''

invoice_fields = {
    'amount': {'string':'Invoiced Amount', 'type':'float', 'required':True, 'readonly':True},
    'amount_topay': {'string':'Amount to pay', 'type':'float', 'required':True, 'readonly':True},
    'amount_paid': {'string':'Amount paid', 'type':'float', 'readonly':True},
    'objects': {'string':'# of objects', 'type':'integer', 'required':True, 'readonly':True},
    'ach_uid': {'string':'Buyer Name', 'type':'many2one', 'required':True, 'relation':'res.partner'},
    'number': {'string':'Invoice Number', 'type':'integer'},
        #'tax_applied':{'string':'Tax Applied', 'type':'float', 'readonly':True},
}

def _get_value(self,cr,uid, datas,context={}):
    service = netsvc.LocalService("object_proxy")
    lots = service.execute(cr,uid, 'auction.lots', 'read', datas['ids'])
    auction = service.execute(cr,uid, 'auction.dates', 'read', [lots[0]['auction_id'][0]])[0]

    price = 0.0
    price_topay = 0.0
    price_paid = 0.0
    #tax=data['form']['tax_applied']
    uid = False
    for lot in lots:
        price_lot = lot['obj_price'] or 0.0

        costs = service.execute(uid, 'auction.lots', 'compute_buyer_costs', [lot['id']])
        for cost in costs:
            price_lot += cost['amount']

        price += price_lot

        if lot['ach_uid']:
            if uid and (lot['ach_uid'][0]<>uid):
                raise wizard.except_wizard('UserError', ('Two different buyers for the same invoice !\nPlease correct this problem before invoicing', 'init'))
            uid = lot['ach_uid'][0]
        elif lot['ach_login']:
            refs = service.execute(uid, 'res.partner', 'search', [('ref','=',lot['ach_login'])])
            if len(refs):
                uid = refs[-1]
        if lot['ach_pay_id']:
            price_paid += price_lot
            #*tax
        else:
            price_topay += price_lot
            #*tax

#TODO: recuperer id next invoice (de la sequence)???
    invoice_number = False
    return {'objects':len(datas['ids']), 'amount':price, 'ach_uid':uid, 'amount_topay':price_topay, 'amount_paid':price_paid, 'number':invoice_number}

def _invoice(self, uid, datas):
    service = netsvc.LocalService("object_proxy")
    service.execute(uid, 'auction.lots', 'lots_invoice_and_cancel_old_invoice', datas['ids'], datas['form']['number'], datas['form']['ach_uid'], 'invoice_open')
    return {}

class wiz_auc_lots_invoice(wizard.interface):
    states = {
        'init': {
            'actions': [_get_value],
            'result': {'type': 'form', 'arch':invoice_form, 'fields': invoice_fields, 'state':[('invoice','Create Invoice'), ('end','Cancel')]}
        },
        'invoice': {
            'actions': [_invoice],
            'result': {'type': 'print', 'report':'auction.invoice', 'state':'end'}
        }
    }
wiz_auc_lots_invoice('auction.lots.invoice');


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

