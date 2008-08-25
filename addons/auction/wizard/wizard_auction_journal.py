# -*- encoding: utf-8 -*-

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

    order_obj = pooler.get_pool(cr.dbname).get('auction.lots')
    newinv = []
    ids = order_obj.seller_trans_create(cr, uid, data['ids'],context)
    cr.commit()
    return {
        'domain': "[('id','in', ["+','.join(map(str,ids))+"])]",
        'name': 'Seller invoices',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.invoice',
        'view_id': False,
        'context': "{'type':'out_refund'}",
        'type': 'ir.actions.act_window'
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

