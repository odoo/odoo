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
import pooler



invoice_form = '''<?xml version="1.0"?>
<form title="Paid ?">
    <field name="amount"/>
    <field name="objects"/>
    <field name="number" colspan="3"/>
</form>'''

invoice_fields = {
    'amount': {'string':'Invoiced Amount', 'type':'float', 'required':True, 'readonly':True},
    'objects': {'string':'# of objects', 'type':'integer', 'required':True, 'readonly':True},
    'number': {'string':'Invoice Number', 'type':'integer'},
}

def _values(self,cr,uid, datas,context={}):
    lots= pooler.get_pool(cr.dbname).get('auction.lots').browse(cr,uid,datas['ids'])
#   service = netsvc.LocalService("object_proxy")
#   lots = service.execute(cr,uid, 'auction.lots', 'read', datas['ids'])
#   auction = service.execute(cr,uid, 'auction.dates', 'read', [lots[0]['auction_id'][0]])[0]
    price = 0.0
    amount_total=0.0
    pt_tax=pooler.get_pool(cr.dbname).get('account.tax')
    for lot in lots:
    #   taxes = lot.product_id.taxes_id
    #   if lot.bord_vnd_id.tax_id:
    #       taxes.append(lot.bord_vnd_id.tax_id)
    #   if lot.auction_id:
    #       taxes += lot.auction_id.seller_costs
    #   tax=pt_tax.compute(cr,uid,taxes,lot.obj_price,1)
    #   for t in tax:
    #       amount_total+=t['amount']
    #   amount_total+=lot.obj_price
        amount_total+=lot.seller_price  
#TODO: recuperer id next invoice (de la sequence)???
    invoice_number = False
    return {'objects':len(datas['ids']), 'amount':amount_total, 'number':invoice_number}

def _makeInvoices(self, cr, uid, data, context):

    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('auction.lots')
    mod_obj = pool.get('ir.model.data') 
    result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
    id = mod_obj.read(cr, uid, result, ['res_id'])
    newinv = []
    ids = order_obj.seller_trans_create(cr, uid, data['ids'],context)
    cr.commit()
    return {
        'domain': "[('id','in', ["+','.join(map(str, ids))+"])]",
        'name': 'Seller invoices',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.invoice',
        'view_id': False,
        'context': "{'type':'out_refund'}",
        'type': 'ir.actions.act_window',
        'search_view_id': id['res_id']        
    }
    return {}

class make_invoice(wizard.interface):
    states = {
        'init' : {
            'actions' : [_values],
            'result' : {'type' : 'form',
                    'arch' : invoice_form,
                    'fields' : invoice_fields,
                    'state' : [('end', 'Cancel'),('invoice', 'Create invoices')]}
        },
        'invoice' : {
            'actions' : [_makeInvoices],
            'result' : {'type' : 'action',
                    'action' : _makeInvoices,
                    'state' : 'end'}
        },
    }
make_invoice("auction.lots.make_invoice")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

