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
import sql_db

buyer_map = '''<?xml version="1.0"?>
<form title="Buyer Map">
    <field name="ach_login"/>
    <newline/>
    <field name="ach_uid"/>
</form>'''

buyer_map_fields = {
    'ach_login': {'string':'Buyer Username', 'type':'char', 'size':64, 'required':True},
    'ach_uid': {'string':'Buyer', 'type':'many2one', 'required':True, 'relation':'res.partner'},
}


#
# Try to find an object not mapped
#
def _state_check(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    cr.execute('select id from auction_lots where (ach_uid is null and ach_login is not null)  ')
    v_ids=[x[0] for x in cr.fetchall()]
    #ids_not_mapped=pool.get('auction.lots').search(cr,uid,[('rec.ach_uid','=',False)])
    for rec in pool.get('auction.lots').browse(cr,uid,v_ids,context):
    #   if not rec.ach_uid and not rec.ach_login:
    #       raise wizard.except_wizard ('Error','No username is associated to this lot!')
        if (not rec.ach_uid or not rec.ach_login):
            return 'check'
    return 'done'

def _start(self,cr,uid,datas,context):
    pool = pooler.get_pool(cr.dbname)
    for rec in pool.get('auction.lots').browse(cr,uid,datas['ids'],context):
        if (len(datas['ids'])==1) and (not rec.ach_uid and not rec.ach_login):
            raise wizard.except_wizard('Error', 'No buyer setted for this lot')
        if not rec.ach_uid and rec.ach_login:
            return {'ach_login': rec.ach_login}

    for rec in pool.get('auction.lots').browse(cr,uid,datas['ids'],context):
        if (not rec.ach_uid and rec.ach_login):
            return {'ach_login': rec.ach_login}
    return {}

def _buyer_map_set(self,cr, uid, datas,context):
    pool = pooler.get_pool(cr.dbname)
    recs=pool.get('auction.lots').browse(cr,uid,datas['ids'],context)
    for rec in recs:
        if rec.ach_login==datas['form']['ach_login']:
            pool.get('auction.lots').write(cr, uid, [rec.id], {'ach_uid':  datas['form']['ach_uid']}, context=context)
            cr.commit()
    return {'ach_login':False, 'ach_uid':False}

class wiz_auc_lots_buyer_map(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'choice', 'next_state':_state_check}
        },
        'check': {
            'actions': [_start],
            'result': {'type': 'form', 'arch':buyer_map, 'fields': buyer_map_fields, 'state':[('end','Exit'),('set_buyer', 'Update')]}
        },
        'set_buyer': {
            'actions': [_buyer_map_set],
            'result': {'type': 'state', 'state':'init'}
        },
        'done': {
            'actions': [_start],
            'result': {
                'type': 'form',
                'arch':'''<?xml version="1.0"?>
                <form title="Mapping result">
                    <label string="All objects are assigned to buyers !"/>
                </form>''',
                'fields': {},
                'state':[('end','Close')]}
        }
    }

wiz_auc_lots_buyer_map('auction.lots.buyer_map')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

