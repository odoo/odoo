# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

import time
import netsvc
from osv import fields, osv
import ir
import pooler
import mx.DateTime
from mx.DateTime import RelativeDateTime
from tools import config

class account_account(osv.osv):
    _inherit = "account.account"
    
    def _get_level(self, cr, uid, ids, field_name, arg, context={}):
        res={}
        acc_obj=self.browse(cr,uid,ids)
        for aobj in acc_obj:
            level = 0
            if aobj.parent_id :
                obj=self.browse(cr,uid,aobj.parent_id.id)
                level= obj.level + 1
            res[aobj.id] = level
        return res
    
    def _get_children_and_consol(self, cr, uid, ids, context={}):
        ids2=[]
        temp=[]
        read_data= self.read(cr, uid, ids,['id','child_id'], context)
        for data in read_data:
            ids2.append(data['id'])
            if data['child_id']:
                temp=[]
                for x in data['child_id']:
                    temp.append(x)
                ids2 += self._get_children_and_consol(cr, uid, temp, context)
        return ids2

    _columns = {

        'journal_id':fields.many2one('account.journal', 'Journal',domain=[('type','=','situation')]),
        'open_bal' : fields.float('Opening Balance',digits=(16,2)),
        'level': fields.function(_get_level, string='Level', method=True, store=True, type='integer'),
        'type1':fields.selection([('dr','Debit'),('cr','Credit'),('none','None')], 'Dr/Cr',store=True),
    }
    
    def compute_total(self, cr, uid, ids, yr_st_date, yr_end_date, st_date, end_date, field_names, context={}):
        if not (st_date >= yr_st_date and end_date <= yr_end_date):
            return {}
        return self.__compute(
            cr, uid, ids, field_names, context=context,
            query="l.date >= '%s' AND l.date <= '%s'",
            query_params=(st_date, end_date))

    def create(self, cr, uid, vals, context={}):
        name=self.search(cr,uid,[('name','ilike',vals['name']),('company_id','=',vals['name'])])
        if name:
            raise osv.except_osv('Error', 'Account is Already Created !')
        obj=self.pool.get('account.account.type').browse(cr,uid,vals['user_type'])
        if obj.code in ('cash','asset','expense'):
            vals['type1'] = 'dr'
        elif obj.code in ('equity','income','liability') : 
             vals['type1'] = 'cr'
        else:
             vals['type1'] = 'none'
        journal_ids=self.pool.get('account.journal').search(cr,uid,[('name','=','Opening Journal')])
        vals['journal_id'] = journal_ids and journal_ids[0] or False
        account_id = super(account_account, self).create(cr, uid, vals, context)
        if vals.get('type1', False) != False:
            journal_id = vals.get('journal_id',False)
            if journal_id and vals.has_key('open_bal'):
                if vals['open_bal'] != 0.0:
                    journal = self.pool.get('account.journal').browse(cr, uid, [journal_id])
                    if journal and journal[0].sequence_id:
                        name = self.pool.get('ir.sequence').get_id(cr, uid, journal[0].sequence_id.id)
                    move=self.pool.get('account.move').search(cr,uid,[('journal_id','=',journal_id)])
                    if not move:
                        move = False
                        move_data = {'name': name, 'journal_id': journal_id}
                        move_id=self.pool.get('account.move').create(cr,uid,move_data)
                        move_obj=self.pool.get('account.move').browse(cr,uid,move_id)
                    else:
                        move_obj=self.pool.get('account.move').browse(cr,uid,move[0])
                    self_obj=self.browse(cr,uid,account_id)
                    move_line = {
                         'name':journal[0].name,
                         'debit':self_obj.debit or False,
                         'credit':self_obj.credit or False,
                         'account_id':account_id or False,
                         'move_id':move and move[0] or move_id,
                         'journal_id':journal_id ,
                         'period_id':move_obj.period_id.id,
                 }
                    if vals['type1'] == 'dr':
                        move_line['debit'] = vals['open_bal'] or False
                    elif vals['type1'] == 'cr':
                        move_line['credit'] = vals['open_bal'] or False
                    self.pool.get('account.move.line').create(cr,uid,move_line)
        return account_id

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        res_temp={}
        if vals.has_key('name'):
            if not vals.has_key('company_id'):
                vals['company_id']=self.browse(cr,uid,ids)[0].company_id.id
            name=self.search(cr,uid,[('name','ilike',vals['name']),('company_id','=',vals['company_id'])])
            if name:
                raise osv.except_osv('Error', 'Same Account Name is Already present !')
        if vals.has_key('user_type'):
            obj=self.pool.get('account.account.type').browse(cr,uid,vals['user_type'])
            if obj.code in ('asset','expense'):
                vals['type1'] = 'dr'
            elif obj.code in ('income','liability') : 
                 vals['type1'] = 'cr'
            else:
                 vals['type1'] = 'none'
        super(account_account, self).write(cr, uid,ids, vals, context)
        if vals.has_key('open_bal'):
            self_obj= self.browse(cr,uid,ids)
            move_pool=self.pool.get('account.move')
            if vals:
                for obj in self_obj:
                    flg=0
                    if obj.journal_id and obj.journal_id.type == 'situation':
                        move=move_pool.search(cr,uid,[('journal_id','=',obj.journal_id.id)])
                        if move:
                            move_obj=move_pool.browse(cr,uid,move[0])
                            move=move[0]
                        else:
                            name = self.pool.get('ir.sequence').get_id(cr, uid, obj.journal_id.sequence_id.id)
                            move_data = {'name': name, 'journal_id': obj.journal_id.id}
                            move=self.pool.get('account.move').create(cr,uid,move_data)
                            move_obj=move_pool.browse(cr,uid,move)
                        move_line_data={'name':obj.journal_id.name,
                                               'debit':obj.debit or 0.0,
                                               'credit':obj.credit or 0.0,
                                               'account_id':obj.id,
                                               'move_id':move,
                                               'journal_id':obj.journal_id.id,
                                               'period_id':move_obj.period_id.id,
                                               }
                        if obj.type1:
                            if obj.type1 == 'dr':
                                move_line_data['debit'] = obj.open_bal
                            elif obj.type1 == 'cr':
                                move_line_data['credit'] = obj.open_bal
                        if move_obj and move:
                            for move_line in move_obj.line_id:
                                if move_line.account_id.id == obj.id:
                                    if move_line_data['debit'] == 0.0 and move_line_data['credit']== 0.0:
                                        self.pool.get('account.move.line').unlink(cr,uid,[move_line.id])
                                    else:
                                        self.pool.get('account.move.line').write(cr,uid,[move_line.id],move_line_data)
                                    flg=1
                            if not flg:
                                self.pool.get('account.move.line').create(cr,uid,move_line_data)
        return True

    def onchange_type(self, cr, uid, ids,user_type,type1):
        if not user_type:
            return {'value' : {}}
        type_obj=self.pool.get('account.account.type').browse(cr,uid,user_type)
        if type_obj.code in ('asset','expense'):
            type1 = 'dr'
        elif type_obj.code in ('income','liability') :
            type1 = 'cr'
        else:
            type1 = 'none'

        return {
            'value' : {'type1' : type1}
    }
account_account()

class account_move(osv.osv):
    _inherit = "account.move"
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'narration':fields.text('Narration', readonly=True, select=True, states={'draft':[('readonly',False)]}),
    }

account_move()

class res_currency(osv.osv):
    _inherit = "res.currency"

    _columns = {
                'sub_name': fields.char('Sub Currency', size=32, required=True)
            }
    _defaults = {
        'sub_name': lambda *a: 'cents',

    }
res_currency()

class account_account_template(osv.osv):
        _inherit = "account.account.template"
        
        _columns = {
        'type1':fields.selection([('dr','Debit'),('cr','Credit'),('none','None')], 'Dr/Cr',store=True),
    }

account_account_template()


