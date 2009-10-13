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

numerotate_form_cont = '''<?xml version="1.0"?>
<form title="%s">
    <field name="number" string="%s"/>
</form>''' % ('Continuous Numerotation','First Number')

numerotate_fields_cont = {
    'number': {'string':'First Number', 'type':'integer', 'required':True}
}

numerotate_not_exist = '''<?xml version="1.0"?>
<form title="%s">
    <label string="This lot does not exist !" colspan="4"/>
</form>''' % ('Catalog Numerotation',)


numerotate_form = '''<?xml version="1.0"?>
<form title="%s">
    <separator string="%s" colspan="4"/>
    <field name="bord_vnd_id"/>
    <newline/>
    <field name="lot_num"/>
</form>''' % ('Catalog Numerotation','Object Reference')

numerotate_fields = {
    'bord_vnd_id': {'string':'Depositer Inventory', 'type':'many2one', 'required':True, 'relation':'auction.deposit'},
    'lot_num': {'string':'Lot Number', 'type':'integer', 'required':True},
}

numerotate_form2 = '''<?xml version="1.0"?>
<form title="%s">
    <group>
        <separator string="%s" colspan="4"/>
        <field name="bord_vnd_id" readonly="1"/>
        <field name="lot_num" readonly="1"/>
        <field name="name" readonly="1" colspan="3"/>
        <field name="obj_desc" readonly="1" colspan="3"/>
        <field name="lot_est1" readonly="1"/>
        <field name="lot_est2" readonly="1"/>
        <separator string="%s" colspan="4"/>
        <field name="obj_num"/>
    </group>
</form>''' % ('Catalog Numerotation','Object Reference','Object Reference')

numerotate_fields2 = {
    'bord_vnd_id': {'string':'Object Inventory', 'type':'many2one', 'relation':'auction.deposit', 'readonly':True},
    'lot_num': {'string':'Inventory Number', 'type':'integer', 'readonly':True},
    'lot_est1': {'string':'Minimum Estimation', 'type':'float', 'readonly':True},
    'lot_est2': {'string':'Maximum Estimation', 'type':'float', 'readonly':True},
    'name': {'string':'Short Description', 'type':'char', 'size':64, 'readonly':True},
    'obj_desc': {'string':'Description', 'type':'text', 'readonly':True},
    'obj_num': {'string':'Catalog Number', 'type':'integer', 'required':True}
}

def _read_record(self,cr,uid,datas,context={}):
    form = datas['form']
    res = pooler.get_pool(cr.dbname).get('auction.lots').search(cr,uid,[('bord_vnd_id','=',form['bord_vnd_id']), ('lot_num','=',int(form['lot_num']))])
    found = [r for r in res if r in datas['ids']]
    if len(found)==0:
        raise wizard.except_wizard('UserError', 'This record does not exist !')
    datas = pooler.get_pool(cr.dbname).get('auction.lots').read(cr,uid,found,['obj_num', 'name', 'lot_est1', 'lot_est2', 'obj_desc'])
    return datas[0]

def _test_exist(self,cr,uid,datas,context={}):
    form = datas['form']
    res = pooler.get_pool(cr.dbname).get('auction.lots').search(cr,uid,[('bord_vnd_id','=',form['bord_vnd_id']), ('lot_num','=',int(form['lot_num']))])
    found = [r for r in res if r in datas['ids']]
    if len(found)==0:
        return 'not_exist'
    return 'search'

def _numerotate(self,cr,uid,datas,context={}):
    form = datas['form']
    res = pooler.get_pool(cr.dbname).get('auction.lots').search(cr,uid,[('bord_vnd_id','=',form['bord_vnd_id']), ('lot_num','=',int(form['lot_num']))])
    found = [r for r in res if r in datas['ids']]
    if len(found)==0:
        raise wizard.except_wizard('UserError', 'This record does not exist !')
    pooler.get_pool(cr.dbname).get('auction.lots').write(cr,uid,found,{'obj_num':int(form['obj_num'])} )
    return {'lot_inv':'', 'lot_num':''}

def _numerotate_cont(self,cr,uid,datas,context={}):
    nbr = int(datas['form']['number'])
    refs = pooler.get_pool(cr.dbname).get('auction.lots')
    rec_ids = refs.browse(cr,uid,datas['ids'])
    for rec_id in rec_ids:
        refs.write(cr,uid,[rec_id.id],{'obj_num':nbr})
        nbr+=1
    return {}

class wiz_auc_lots_numerotate(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':numerotate_form, 'fields': numerotate_fields, 'state':[('end','Cancel'),('choice','Continue')]}
        },
        'search': {
            'actions': [_read_record],
            'result': {'type': 'form', 'arch':numerotate_form2, 'fields': numerotate_fields2, 'state':[('end','Exit'),('init','Back'),('set_number','Numerotate')]}
        },
        'choice' : {
            'actions' : [],
            'result' : {'type' : 'choice', 'next_state': _test_exist }
        },
        'not_exist' : {
            'actions': [],
            'result': {'type': 'form', 'arch':numerotate_not_exist, 'fields': {}, 'state':[('end','Exit'),('init','Retry')]}
        },
        'set_number': {
            'actions': [_numerotate],
            'result': {'type': 'state', 'state':'init'}
        }
    }
wiz_auc_lots_numerotate('auction.lots.numerotate');


class wiz_auc_lots_numerotate(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':numerotate_form_cont, 'fields': numerotate_fields_cont, 'state':[('end','Exit'),('set_number','Numerotation')]}
        },
        'set_number': {
            'actions': [_numerotate_cont],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_auc_lots_numerotate('auction.lots.numerotate_cont');
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

