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
import netsvc
import pooler

invoice_form = '''<?xml version="1.0"?>
<form title="Paid ?">
    <field name="amount"/>
    <field name="objects"/>
    <field name="number"/>
    <label string="(Keep empty for automatic number)" colspan="2"/>
    <field name="buyer_id"/>
</form>'''

invoice_fields = {
    'amount': {'string':'Invoiced Amount', 'type':'float', 'required':True, 'readonly':True},
    'objects': {'string':'# of objects', 'type':'integer', 'required':True, 'readonly':True},
    'number': {'string':'Invoice Number', 'type':'char'},
    'buyer_id':{'string': 'Buyer', 'type': 'many2one', 'relation':'res.partner'}

}


def _values(self,cr,uid, datas,context={}):
    pool = pooler.get_pool(cr.dbname)
    lots= pool.get('auction.lots').browse(cr,uid,datas['ids'])
#   price = 0.0
    amount_total=0.0
#   pt_tax=pooler.get_pool(cr.dbname).get('account.tax')
    for lot in lots:
        buyer=lot and lot.ach_uid.id or False
        amount_total+=lot.buyer_price
#       taxes = lot.product_id.taxes_id
#       if lot.author_right:
#           taxes.append(lot.author_right)
#       if lot.auction_id:
#           taxes += lot.auction_id.buyer_costs
#       tax=pt_tax.compute(cr,uid,taxes,lot.obj_price,1)
#       for t in tax:
#           amount_total+=t['amount']
#       amount_total+=lot.obj_price
    #   up_auction=pooler.get_pool(cr.dbname).get('auction.lots').write(cr,uid,[lot.id],{'ach_uid':datas['form']['buyer_id']})
    invoice_number = False
    return {'objects':len(datas['ids']), 'amount':amount_total, 'number':invoice_number,'buyer_id':buyer}


def _makeInvoices(self, cr, uid, data, context):
    newinv = []
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('auction.lots')
    mod_obj = pool.get('ir.model.data') 
    result = mod_obj._get_id(cr, uid, 'account', 'view_account_invoice_filter')
    id = mod_obj.read(cr, uid, result, ['res_id'])
    lots= order_obj.browse(cr,uid,data['ids'])
    invoice_number=data['form']['number']
    for lot in lots:
        up_auction=pooler.get_pool(cr.dbname).get('auction.lots').write(cr,uid,[lot.id],{'ach_uid':data['form']['buyer_id']})
    ids = order_obj.lots_invoice(cr, uid, data['ids'],context,data['form']['number'])
#   ids = order_obj.lots_invoice(cr, uid, data['ids'],context,invoice_number)
    cr.commit()
    return {
        'domain': "[('id','in', ["+','.join(map(str,ids))+"])]",
        'name': 'Buyer invoices',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.invoice',
        'view_id': False,
        'context': "{'type':'in_refund'}",
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
            'actions' : [],
            'result' : {'type' : 'action',
                    'action' : _makeInvoices}
        },
    }
make_invoice("auction.lots.make_invoice_buyer")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

