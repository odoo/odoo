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

import time
import wizard
import netsvc
import pooler
from osv.orm import browse_record
import sql_db

transfer_unsold_object_form = """<?xml version="1.0"?>
<form string="Draft To Posted">
    <group col="1" colspan="2">
    <separator colspan="4" string="Transfer unsold Object: Current auction date to another " />
    </group>
    <newline/>
    <field name="auction_id_from"/>
    <newline/>
    <field name="auction_id_to"/>
</form>
"""

transfer_unsold_object_fields = {
         'auction_id_from': {'string':'From Auction Date', 'type':'many2one', 'required':True, 'relation':'auction.dates'},
         'auction_id_to': {'string':'To Auction Date', 'type':'many2one', 'required':True, 'relation':'auction.dates'},
}

def _start(self,cr,uid,data,context):
    pool = pooler.get_pool(cr.dbname)
    rec=pool.get('auction.lots').browse(cr,uid,data['id'],context)
    auction_from= rec and rec.auction_id.id or False
    return {'auction_id_from':auction_from}

def _transfer_unsold_object(self, cr, uid, data, context):
    #if not (data['form']['auction_id_to']) :
    #   return {}
#Historique de l objet + changement de l auction date + supp des bid line
    line_ids= pooler.get_pool(cr.dbname).get('auction.bid_line').search(cr,uid,[('lot_id','in',data['ids'])])
    pooler.get_pool(cr.dbname).get('auction.bid_line').unlink(cr, uid, line_ids)
    
    obj_pool = pooler.get_pool(cr.dbname).get('auction.lots')
    ids= obj_pool.search(cr,uid,[('auction_id','=',data['form']['auction_id_from']),('state','=','unsold')])
    for rec in obj_pool.browse(cr, uid, ids, context):
        new_id=pooler.get_pool(cr.dbname).get('auction.lot.history').create(cr,uid,{'auction_id':rec.auction_id.id,'lot_id':rec.id,'price': rec.obj_ret, 'name': 'reasons'+rec.auction_id.auction1})
        up_auction=pooler.get_pool(cr.dbname).get('auction.lots').write(cr,uid,[rec.id],{'auction_id':data['form']['auction_id_to'],
                                                                                        'obj_ret':None,
                                                                                        'obj_price':None,
                                                                                        'ach_login':None,
                                                                                        'ach_uid':None,
                                                                                        'ach_inv_id':None,
                                                                                        'sel_inv_id':None,
                                                                                        'state':'draft'})

        #   new_id = self.pool.get('auction.lot.history').copy(cr, uid, m.id, {'price': recs.obj_ret, 'name': 'reasons'+recs.auction_id.name})
    #           new_id=pooler.get_pool(cr.dbname).get('auction.lot.history').create(cr,uid,{'auction_id':rec.auction_id,'lot_id':rec.name,'price': rec.obj_ret, 'name': 'reasons'+rec.auction_id.auction1})
    return {}

class transfer_object(wizard.interface):
    states = {
        'init' : {
            'actions' : [_start],
            'result' : {'type' : 'form',
                    'arch' : transfer_unsold_object_form,
                    'fields' :transfer_unsold_object_fields,
                    'state' : [('transfer', 'Transfer'),('end', 'Cancel') ]}
        },
        'transfer' : {
            'actions' : [_transfer_unsold_object],
            'result' : {'type' : 'state','state' : 'end'}
        },
    }
transfer_object('auction.lots.transfer.unsold.object')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

