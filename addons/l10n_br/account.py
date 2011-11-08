# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
# Copyright (C) 2009  Renato Lima - Akretion                                    #
#                                                                               #
#This program is free software: you can redistribute it and/or modify           #
#it under the terms of the GNU Affero General Public License as published by    #
#the Free Software Foundation, either version 3 of the License, or              #
#(at your option) any later version.                                            #
#                                                                               #
#This program is distributed in the hope that it will be useful,                #
#but WITHOUT ANY WARRANTY; without even the implied warranty of                 #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                  #
#GNU General Public License for more details.                                   #
#                                                                               #
#You should have received a copy of the GNU General Public License              #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.          #
#################################################################################

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from operator import itemgetter

import netsvc
import pooler
from osv import fields, osv
import decimal_precision as dp
from tools.misc import currency
from tools.translate import _
from tools import config

class account_tax_code_template(osv.osv):

    _inherit = 'account.tax.code.template'
    _columns = {
                'domain':fields.char('Domain', size=32, help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain."),
                'tax_discount': fields.boolean('Discount this Tax in Prince', help="Mark it for (ICMS, PIS e etc.)."),
        }
account_tax_code_template()

class account_tax_code(osv.osv):

    _inherit = 'account.tax.code'
    _columns = {
                'domain':fields.char('Domain', size=32, help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain."),
                'tax_discount': fields.boolean('Discount this Tax in Prince', help="Mark it for (ICMS, PIS e etc.)."),
        }
account_tax_code()

class account_tax_template(osv.osv):
    _inherit = 'account.tax.template'
    
    def get_precision_tax():
        def change_digit_tax(cr):
            res = pooler.get_pool(cr.dbname).get('decimal.precision').precision_get(cr, 1, 'Account')
            return (16, res+2)
        return change_digit_tax
    
    _columns = {
                'tax_discount': fields.boolean('Discount this Tax in Prince', help="Mark it for (ICMS, PIS e etc.)."),
                'base_reduction': fields.float('Redution', required=True, digits_compute=get_precision_tax(), help="For taxes of type percentage, enter % ratio between 0-1."),
                'amount_mva': fields.float('MVA Percent', required=True, digits_compute=get_precision_tax(), help="For taxes of type percentage, enter % ratio between 0-1."),
                'type': fields.selection( [('percent','Percentage'), ('fixed','Fixed Amount'), ('none','None'), ('code','Python Code'), ('balance','Balance'), ('quantity','Quantity')], 'Tax Type', required=True,
                                          help="The computation method for the tax amount."),
    }
    _defaults = {
                'base_reduction': 0,
                'amount_mva': 0,
    }
    
    def onchange_tax_code_id(self, cr, uid, ids, tax_code_id, context=None):
        
        result = {'value': {}}
            
        if not tax_code_id:
            return result
        
        obj_tax_code = self.pool.get('account.tax.code.template').browse(cr, uid, tax_code_id)     
    
        if obj_tax_code:
            result['value']['tax_discount'] = obj_tax_code.tax_discount
            result['value']['domain'] = obj_tax_code.domain

        return result

account_tax_template()

class account_tax(osv.osv):
    _inherit = 'account.tax'
    
    def get_precision_tax():
        def change_digit_tax(cr):
            res = pooler.get_pool(cr.dbname).get('decimal.precision').precision_get(cr, 1, 'Account')
            return (16, res+2)
        return change_digit_tax
    
    _columns = {
                'tax_discount': fields.boolean('Discount this Tax in Prince', help="Mark it for (ICMS, PIS e etc.)."),
                'base_reduction': fields.float('Redution', required=True, digits_compute=get_precision_tax(), help="Um percentual decimal em % entre 0-1."),
                'amount_mva': fields.float('MVA Percent', required=True, digits_compute=get_precision_tax(), help="Um percentual decimal em % entre 0-1."),
                'type': fields.selection( [('percent','Percentage'), ('fixed','Fixed Amount'), ('none','None'), ('code','Python Code'), ('balance','Balance'), ('quantity','Quantity')], 'Tax Type', required=True,
                                          help="The computation method for the tax amount."),
    }
    _defaults = {
                 'base_reduction': 0,
                 'amount_mva': 0,
    }
    
    def onchange_tax_code_id(self, cr, uid, ids, tax_code_id, context=None):
        
        result = {'value': {}}
            
        if not tax_code_id:
            return result
        
        obj_tax_code = self.pool.get('account.tax.code').browse(cr, uid, tax_code_id)      
    
        if obj_tax_code:
            result['value']['tax_discount'] = obj_tax_code.tax_discount
            result['value']['domain'] = obj_tax_code.domain

        return result

account_tax()

class account_journal(osv.osv):
    _inherit = "account.journal"

    _columns = {
                'internal_sequence': fields.many2one('ir.sequence', 'Internal Sequence'),
    }

account_journal()

class wizard_multi_charts_accounts(osv.osv_memory):

    _inherit = 'wizard.multi.charts.accounts'
    
    def execute(self, cr, uid, ids, context=None):
        
        super(wizard_multi_charts_accounts, self).execute(cr, uid, ids, context)
        
        obj_multi = self.browse(cr, uid, ids[0])
        obj_acc_tax = self.pool.get('account.tax')
        obj_acc_tax_tmp = self.pool.get('account.tax.template')
        obj_acc_cst = self.pool.get('l10n_br_account.cst')
        obj_acc_cst_tmp = self.pool.get('l10n_br_account.cst.template')
        obj_tax_code = self.pool.get('account.tax.code')
        obj_tax_code_tmp = self.pool.get('account.tax.code.template')

        # Creating Account
        obj_acc_root = obj_multi.chart_template_id.account_root_id
        tax_code_root_id = obj_multi.chart_template_id.tax_code_root_id.id
        company_id = obj_multi.company_id.id
        
        children_tax_code_template = self.pool.get('account.tax.code.template').search(cr, uid, [('parent_id','child_of',[tax_code_root_id])], order='id')
        children_tax_code_template.sort()
        for tax_code_template in self.pool.get('account.tax.code.template').browse(cr, uid, children_tax_code_template, context=context):
            tax_code_id = self.pool.get('account.tax.code').search(cr, uid, [('code','=',tax_code_template.code),('company_id','=',company_id)])
            if tax_code_id:
                obj_tax_code.write(cr, uid, tax_code_id, {'domain': tax_code_template.domain,'tax_discount': tax_code_template.tax_discount})
            
                cst_tmp_ids = self.pool.get('l10n_br_account.cst.template').search(cr, uid, [('tax_code_template_id','=',tax_code_template.id)], order='id')
                for cst_tmp in self.pool.get('l10n_br_account.cst.template').browse(cr, uid, cst_tmp_ids, context=context):
                    obj_acc_cst.create(cr, uid, {
                                                 'code': cst_tmp.code,
                                                 'name': cst_tmp.name,
                                                 'tax_code_id': tax_code_id[0],
                                                 })
            
        tax_ids = self.pool.get('account.tax').search(cr, uid, [('company_id','=',company_id)])
        for tax in self.pool.get('account.tax').browse(cr, uid, tax_ids, context=context):
            if tax.tax_code_id:
                obj_acc_tax.write(cr, uid, tax.id, {'domain': tax.tax_code_id.domain,'tax_discount': tax.tax_code_id.tax_discount})
        
wizard_multi_charts_accounts()