# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from tools.translate import _

class hr_payroll_create_analytic(osv.osv_memory):
   _name = "hr.payroll.create.analytic"
   _columns = {
        'company_id': fields.many2one('res.company', 'Company'),
        'type': fields.selection([('bydeg','By Employee Function'), ('byallded','By Allownce / Deduction')],'Type'),
       }

   def do_duplicate(self, cr, uid, ids, context=None):
        account_pool = self.pool.get('account.analytic.account')
        func_pool = self.pool.get('hr.employee.grade')
        ad_pool = self.pool.get('hr.allounce.deduction.categoty')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        tpy = data['type']
        company = data['company_id']

        function_ids = func_pool.search(cr, uid, [], context=context)
        ad_ids = ad_pool.search(cr, uid, [], context=context)

        if tpy == 'bydeg':
            for function in func_pool.browse(cr, uid, function_ids, context=context):
                res = {
                    'name':function.name,
                    'company_id':company
                }
                fid = account_pool.create(cr, uid, res, context=context)
                res = {
                    'name':'Basic Salary',
                    'company_id':company,
                    'parent_id': fid
                }
                account_pool.create(cr, uid, res, context=context)
                for ad in ad_pool.browse(cr, uid, ad_ids, context=context):
                    res = {
                        'name':ad.name,
                        'company_id':company,
                        'parent_id': fid
                    }
                    account_pool.create(cr, uid, res, context=context)



        elif tpy == 'byallded':
            res = {
                'name':'Basic Salary',
                'company_id':company
            }
            adid = account_pool.create(cr, uid, res, context=context)
            for function in func_pool.browse(cr, uid, function_ids, context=context):
                res = {
                    'name':function.name,
                    'company_id':company,
                    'parent_id': adid
                }
                account_pool.create(cr, uid, res, context=context)

            for ad in ad_pool.browse(cr, uid, ad_ids, context=context):
                res = {
                    'name':ad.name,
                    'company_id':company,
                }
                adid = account_pool.create(cr, uid, res, context=context)
                for function in func_pool.browse(cr, uid, function_ids, context=context):
                    res = {
                        'name':function.name,
                        'company_id':company,
                        'parent_id': adid
                    }
                    account_pool.create(cr, uid, res, context=context)

        return {}
hr_payroll_create_analytic()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
