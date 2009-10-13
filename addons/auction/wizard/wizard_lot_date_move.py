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
import sql_db

auction_move = '''<?xml version="1.0"?>
<form string="Change Auction Date">
    <group col="1" colspan="2">
    <label string="Warning, this will erase the object adjudication price and its buyer !" colspan="2"/>
    </group>
    <newline/>
    <field name="auction_id"/>
</form>'''

auction_move_fields = {
    'auction_id': {'string':'Auction Date', 'type':'many2one', 'required':True, 'relation':'auction.dates'},
}

#def _auction_move_set(self, uid, datas):
#   if datas['form']['auction_id']:
#       cr = sql_db.db.cursor()
#       cr.execute('update auction_lots set auction_id=%s, obj_price=NULL, ach_login=NULL, ach_uid=NULL, ach_pay_id=NULL, ach_inv_id=NULL, state=%s where id in ('+','.join(map(str, datas['ids']))+')', (str(datas['form']['auction_id']), 'draft'))
#       cr.execute('delete from auction_bid_line where lot_id in ('+','.join(map(str, datas['ids']))+')')
#       cr.commit()
#       cr.close()
#   return {}
def _top(self,cr,uid,datas,context={}):
    refs = pooler.get_pool(cr.dbname).get('auction.lots')
    rec_ids = refs.browse(cr,uid,datas['ids'])
    for rec in rec_ids:
        if not rec.auction_id:
            raise wizard.except_wizard('Error !','You can not move a lot that has no auction date')
    return {}
def _auction_move_set(self,cr,uid,datas,context={}):
    if not (datas['form']['auction_id'] and len(datas['ids'])) :
        return {}
    refs = pooler.get_pool(cr.dbname).get('auction.lots')
    rec_ids = refs.browse(cr,uid,datas['ids'])
    
    line_ids= pooler.get_pool(cr.dbname).get('auction.bid_line').search(cr,uid,[('lot_id','in',datas['ids'])])
#   pooler.get_pool(cr.dbname).get('auction.bid_line').unlink(cr, uid, line_ids)
    for rec in rec_ids:
        new_id=pooler.get_pool(cr.dbname).get('auction.lot.history').create(cr,uid,{
            'auction_id':rec.auction_id.id,
            'lot_id':rec.id,
            'price': rec.obj_ret
        })
        up_auction=pooler.get_pool(cr.dbname).get('auction.lots').write(cr,uid,[rec.id],{
            'auction_id':datas['form']['auction_id'],
            'obj_ret':None,
            'obj_price':None,
            'ach_login':None,
            'ach_uid':None,
            'ach_inv_id':None,
            'sel_inv_id':None,
            'obj_num':None,
            'state':'draft'})
    return {}

class wiz_auc_lots_auction_move(wizard.interface):
    states = {
        'init': {
            'actions': [_top],
            'result': {'type': 'form', 'arch':auction_move, 'fields': auction_move_fields, 'state':[('set_date', 'Move to Auction date'),('end','Cancel')]}
        },
        'set_date': {
            'actions': [_auction_move_set],
            'result': {'type': 'state', 'state':'end'}
        }
    }

wiz_auc_lots_auction_move('auction.lots.auction_move')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

