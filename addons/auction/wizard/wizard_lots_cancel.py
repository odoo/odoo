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

paid_form = '''<?xml version="1.0"?>
<form string="Cancel Payment">
    <label string="Are you sure you want to refund this invoice ?"/>
</form>'''
fields_ask = {
}
#
#def _get_value(self,cr,uid, datas,context={}):
##  service = netsvc.LocalService("object_proxy")
#   lots=pool.get('auction.lots').browse(cr,uid,data['id'],context)
#
#   
##  lots = service.execute(cr.dbname,uid, 'auction.lots', 'read', datas['ids'])
#
#   ids = []
#   pay_ids = {}
#   price = 0.0
#   price_paid = 0.0
#   uid = False
#
##TODO: refuse if several payments?
#   for lot in lots:
#           price += lot['obj_price']
#
#           # add all the buyer costs
#           costs = service.execute(cr.dbname,uid, 'auction.lots', 'compute_buyer_costs', [lot['id']])
#           for cost in costs:
#               price += cost['amount']
#
##TODO: pr bien faire, faudrait leur poser la question: continue anyway?
#   if len(ids)<len(datas['ids']):
#       raise wizard.except_wizard('UserError', ('Some object(s) are not paid !', 'init'))
#
#   return {'objects':len(ids), 'amount_total':price, 'amount_paid':price_paid}
#
#def _cancel(self, uid, datas):
#   service = netsvc.LocalService("object_proxy")
#   lots = service.execute(cr.dbname,uid, 'auction.lots', 'lots_cancel_payment', datas['ids'])
#   return {}
#

def _cancel(self,cr,uid,data,context):
    pool = pooler.get_pool(cr.dbname)
    lot = pool.get('auction.lots').browse(cr,uid,data['id'],context)
    if lot.ach_inv_id:
        p=pool.get('account.invoice').refund(['lot.ach_inv_id.id'],context)
    if lot.vnd_inv_id:
        p=pool.get('account.invoice').refund(['lot.vnd_inv_id.id'],context)
    return {}

class wiz_auc_lots_cancel(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':paid_form, 'fields': fields_ask, 'state':[('make_cancel','Cancel Payment'), ('end','Cancel')]}
        },
        'make_cancel': {
            'actions': [_cancel],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_auc_lots_cancel('auction.lots.cancel');


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

