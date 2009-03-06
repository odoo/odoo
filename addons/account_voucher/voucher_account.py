# -*- encoding: utf-8 -*-
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
import time
import netsvc
from osv import fields, osv
import ir
import pooler
import mx.DateTime
from mx.DateTime import RelativeDateTime

from tools import config

class Account(osv.osv):
        _inherit = "account.account"
        
        def __compute(self, cr, uid, ids, field_names, arg, context={}, query=''):
            #compute the balance/debit/credit accordingly to the value of field_name for the given account ids
            mapping = {
                'balance': "COALESCE(SUM(l.debit) - SUM(l.credit) , 0) as balance ",
                'debit': "COALESCE(SUM(l.debit), 0) as debit ",
                'credit': "COALESCE(SUM(l.credit), 0) as credit "
            }
            #get all the necessary accounts
            ids2 = self._get_children_and_consol(cr, uid, ids, context)
            acc_set = ",".join(map(str, ids2))
            #compute for each account the balance/debit/credit from the move lines
            accounts = {}
            if ids2:
                query = self.pool.get('account.move.line')._query_get(cr, uid,
                        context=context)
                cr.execute(("SELECT l.account_id as id, " +\
                        ' , '.join(map(lambda x: mapping[x], field_names)) +
                        "FROM " \
                            "account_move_line l " \
                        "WHERE " \
                            "l.account_id IN (%s) " \
                            "AND " + query + " " \
                        "GROUP BY l.account_id") % (acc_set, ))
    
                for res in cr.dictfetchall():
                    accounts[res['id']] = res
    
            #for the asked accounts, get from the dictionnary 'accounts' the value of it
            res = {}
            for id in ids:
                res[id] = self._get_account_values(cr, uid, id, accounts, field_names, context)
            for id in ids:    
                open=self.browse(cr, uid, id, context)
                type_id=open.user_type
                obj=self.pool.get('account.account.type').browse(cr,uid,type_id.id)
                open_balance=open.open_bal
                if obj.code in ('cash','asset','expense'):
                    res[id]['balance']+=open_balance
                elif obj.code in ('equity','income','liability'):
                    total=open_balance*(-1)
                    res[id]['balance']+=total
                else:
                    res[id]=res[id]
            return res
        
        def _get_account_values(self, cr, uid, id, accounts, field_names, context={}):
            res = {}.fromkeys(field_names, 0.0)
            browse_rec = self.browse(cr, uid, id)
            if browse_rec.type == 'consolidation':
                ids2 = self.read(cr, uid, [browse_rec.id], ['child_consol_ids'], context)[0]['child_consol_ids']
                for t in self.search(cr, uid, [('parent_id', 'child_of', [browse_rec.id])]):
                    if t not in ids2 and t != browse_rec.id:
                        ids2.append(t)
                for i in ids2:
                    tmp = self._get_account_values(cr, uid, i, accounts, field_names, context)
                    for a in field_names:
                        res[a] += tmp[a]
            else:
                ids2 = self.search(cr, uid, [('parent_id', 'child_of', [browse_rec.id])])
                for i in ids2:
                    for a in field_names:
                        res[a] += accounts.get(i, {}).get(a, 0.0)
            return res
           
        def _diff(self, cr, uid, ids, field_name, arg, context={}):

            res={}
            dr_total=0.0
            cr_total=0.0
            difference=0.0
            for id in ids:
                open=self.browse(cr, uid, id, context)
                if open.type1 == 'dr':
                    dr_total+=open.open_bal
                elif open.type1 == 'cr':
                    cr_total+=open.open_bal
                else:
                    difference=0.0
            difference=dr_total-cr_total
            for id in ids:
                res[id]=difference
            return res

        _columns = {
            'open_bal' : fields.float('Opening Balance',digits=(16,2)),
            'diff' : fields.function(_diff, digits=(16,2),method=True,string='Difference of Opening Bal.'),
            'type1':fields.selection([('dr','Debit'),('cr','Credit'),('none','None')], 'Dr/Cr',store=True),
            'balance': fields.function(__compute, digits=(16,2), method=True, string='Closing Balance', multi='balance'),
            'credit': fields.function(__compute, digits=(16,2), method=True, string='Credit', multi='balance'),
            'debit': fields.function(__compute, digits=(16,2), method=True, string='Debit', multi='balance'),


    }
        
    
        def onchange_type(self, cr, uid, ids,user_type,type1):
            obj=self.pool.get('account.account.type').browse(cr,uid,user_type)
            account_type=obj.code
            if not account_type:
                return {'value' : {}}
            if account_type in ('cash','asset','expense'):
                type1 = 'dr'
            elif account_type in ('equity','income','liability') : 
                type1 = 'cr'
            else:
                type1 = 'none'
          
            return {
                'value' : {'type1' : type1}
        }

Account()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
