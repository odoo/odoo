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
import datetime
from dateutil.relativedelta import relativedelta

from operator import itemgetter
from osv import fields, osv
import netsvc

class account_installer(osv.osv_memory):
    _name = 'account.installer'
    _inherit = 'res.config.installer'

    def _get_charts(self, cr, uid, context=None):
        modules = self.pool.get('ir.module.module')
        ids = modules.search(cr, uid, [('category_id','=','Account Charts')])
        charts = list(
            sorted(((m.name, m.shortdesc)
                    for m in modules.browse(cr, uid, ids)),
                   key=itemgetter(1)))
        charts.insert(0,('configurable','Configurable Chart of Account'))
        return charts

#    def default_get(self, cr, uid, fields_list=None, context=None):
#         ''' set default accounts'''
#         defaults = super(account_installer, self)\
#         .default_get(cr, uid, fields_list=fields_list, context=context)
#         account = self.pool.get('account.bank.accounts.wizard')
#         ids = []
#         for acc in ('Current','Deposit'):
#             ids.append(account.create(cr, uid, {'acc_name':acc,'account_type':'cash','bank_account_id':self}))
#         defaults.update({'bank_accounts_id':[(6,0,ids)]})
#         return defaults

    _columns = {
        # Accounting
        'charts':fields.selection(_get_charts, 'Chart of Accounts',
            required=True,
            help="Installs localized accounting charts to match as closely as "
                 "possible the accounting needs of your company based on your "
                 "country."),
        'account_analytic_plans':fields.boolean('Multiple Analytic Plans',
            help="Allows invoice lines to impact multiple analytic accounts "
                 "simultaneously."),
        'account_payment':fields.boolean('Suppliers Payment Management',
            help="Streamlines invoice payment and creates hooks to plug "
                 "automated payment systems in."),
        'account_followup':fields.boolean('Followups Management',
            help="Helps you generate reminder letters for unpaid invoices, "
                 "including multiple levels of reminding and customized "
                 "per-partner policies."),
        'account_asset':fields.boolean('Assets Management',
            help="Enables asset management in the accounting application, "
                 "including asset categories and usage periods."),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period':fields.selection([('month','Monthly'), ('3months','3 Monthly')],
                                  'Periods', required=True),
        'bank_accounts_id': fields.one2many('account.bank.accounts.wizard', 'bank_account_id', 'Bank Accounts',required=True),
        'sale_tax':fields.float('Sale Tax(%)'),
        'purchase_tax':fields.float('Purchase Tax(%)')
        }
    _defaults = {
        'date_start': lambda *a: time.strftime('%Y-01-01'),
        'date_stop': lambda *a: time.strftime('%Y-12-31'),
        'period':lambda *a:'month',
        'sale_tax':lambda *a:0.0,
        'purchase_tax':lambda *a:0.0,
        }

    def on_change_start_date(self, cr, uid, id, start_date):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_date = (start_date + relativedelta(months=12)) - relativedelta(days=1)
            return {'value':{'date_stop':end_date.strftime('%Y-%m-%d')}}
        return {}

    def execute(self, cr, uid, ids, context=None):
        super(account_installer, self).execute(cr, uid, ids, context=context)
        record = self.browse(cr, uid, ids, context=context)[0]
        for res in self.read(cr,uid,ids):
            if record.charts == 'configurable':
                obj_acc = self.pool.get('account.account')
                obj_tax = self.pool.get('account.tax')
                user_type = self.pool.get('account.account.type')
                obj_product = self.pool.get('product.product')
                ir_values = self.pool.get('ir.values')
                u_type_id = user_type.search(cr, uid,[('name','ilike','view')])[0]
                company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
                vals = {'name': company.name or '',
                        'currency_id': company.currency_id.id or False,
                        'code': 0 or '',
                        'type': 'view',
                        'user_type': u_type_id,
                        'company_id': company.id }
                main_account = obj_acc.create(cr, uid, vals)
                for val in record.bank_accounts_id:
                    vals = {'name': val.acc_name or '',
                        'currency_id': val.currency_id.id or False,
                        'code': val.acc_name or '',
                        'type': 'view',
                        'user_type': u_type_id,
                        'parent_id':main_account,
                        'company_id': company.id }
                    obj_acc.create(cr, uid, vals)

                sales_tax = obj_tax.create(cr, uid,{'name':'sale Tax','amount':res.get('sale_tax',0.0)})
                purchase_tax = obj_tax.create(cr, uid,{'name':'purchase Tax','amount':res.get('purchase_tax',0.0)})
                product_ids = obj_product.search(cr,uid, [])
                for product in obj_product.browse(cr, uid, product_ids):
                    obj_product.write(cr, uid, product.id, {'taxes_id':[(6,0,[sales_tax])],'supplier_taxes_id':[(6,0,[purchase_tax])]})
                for name, value in [('taxes_id',sales_tax),('supplier_taxes_id',purchase_tax)]:
                    ir_values.set(cr, uid, key='default', key2=False, name=name, models =[('product.product',False)], value=[value])

            if 'date_start' in res and 'date_stop' in res:
                name = code = res['date_start'][:4]
                if int(name) != int(res['date_stop'][:4]):
                    name = res['date_start'][:4] +'-'+ res['date_stop'][:4]
                    code = res['date_start'][2:4] +'-'+ res['date_stop'][2:4]
                res_obj = self.pool.get('account.fiscalyear')
                vals = {'name':name,
                        'code':code,
                        'date_start':res['date_start'],
                        'date_stop':res['date_stop'],
                       }
                period_id = res_obj.create(cr, uid, vals, context=context)
                if res['period'] == 'month':
                    res_obj.create_period(cr, uid, [period_id])
                elif res['period'] == '3months':
                    res_obj.create_period3(cr, uid, [period_id])

    def modules_to_install(self, cr, uid, ids, context=None):
        modules = super(account_installer, self).modules_to_install(
            cr, uid, ids, context=context)
        chart = self.read(cr, uid, ids, ['charts'],
                          context=context)[0]['charts']
        self.logger.notifyChannel(
            'installer', netsvc.LOG_DEBUG,
            'Installing chart of accounts %s'%chart)
        return modules | set([chart])


account_installer()

class account_bank_accounts_wizard(osv.osv_memory):
    _name='account.bank.accounts.wizard'

    _columns = {
        'acc_name':fields.char('Account Name.', size=64, required=True),
        'bank_account_id':fields.many2one('wizard.multi.charts.accounts', 'Bank Account', required=True),
        'currency_id':fields.many2one('res.currency', 'Currency'),
        'account_type':fields.selection([('cash','Cash'),('check','Check'),('bank','Bank')], 'Type', size=32),
    }
    _defaults = {
        'currency_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
        }

account_bank_accounts_wizard()
