#!/usr/bin/env python
#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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
import pooler

class wizard_create_analytics(wizard.interface):
    '''
    OpenERP Wizard
    '''
    form = '''<?xml version="1.0"?>
    <form string="Process Form">
        <field name="company_id"/>
        <newline/>
        <field name="type"/>
    </form>'''

    fields = {
        'company_id': {'string': 'Company', 'type': 'many2one', 'relation': 'res.company'},
        'type': {'string':'Type', 'type':'selection', 'selection':[('bydeg','By Employee Function'), ('byallded','By Allownce / Deduction')]}
    }

    def _get_defaults(self, cr, user, data, context):
        #TODO : initlize required data
        
        
        return data['form'] 

    def _do_duplicate(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        account_pool = pool.get('account.analytic.account')
        func_pool = pool.get('hr.employee.grade')
        ad_pool = pool.get('hr.allounce.deduction.categoty')
        
        tpy = data['form']['type']
        company = data['form']['company_id']
        
        function_ids = func_pool.search(cr, uid, [])
        ad_ids = ad_pool.search(cr, uid, [])
        
        if tpy == 'bydeg':
            for function in func_pool.browse(cr, uid, function_ids):
                res = {
                    'name':function.name,
                    'company_id':company
                }
                fid = account_pool.create(cr, uid, res)
                res = {
                    'name':'Basic Salary',
                    'company_id':company,
                    'parent_id': fid
                }
                account_pool.create(cr, uid, res)
                for ad in ad_pool.browse(cr, uid, ad_ids):
                    res = {
                        'name':ad.name,
                        'company_id':company,
                        'parent_id': fid
                    }
                    account_pool.create(cr, uid, res)
                    
                    
            
        elif tpy == 'byallded':
            res = {
                'name':'Basic Salary',
                'company_id':company
            }
            adid = account_pool.create(cr, uid, res)
            for function in func_pool.browse(cr, uid, function_ids):
                res = {
                    'name':function.name,
                    'company_id':company,
                    'parent_id': adid
                }
                account_pool.create(cr, uid, res)
            
            for ad in ad_pool.browse(cr, uid, ad_ids):
                res = {
                    'name':ad.name,
                    'company_id':company,
                }
                adid = account_pool.create(cr, uid, res)
                for function in func_pool.browse(cr, uid, function_ids):
                    res = {
                        'name':function.name,
                        'company_id':company,
                        'parent_id': adid
                    }
                    account_pool.create(cr, uid, res)
            
        return {}
    
    states = {
        'init': {
            'actions': [_get_defaults],
            'result': {'type': 'form', 'arch': form, 'fields': fields, 'state': (('end', 'Cancel'), ('process', 'Process'))},
        },
        'process': {
            'actions': [_do_duplicate],
            'result': {'type': 'state', 'state': 'end'},
        },
    }
wizard_create_analytics('payroll.analysis')
