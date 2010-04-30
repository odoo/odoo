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
        charts.insert(0,('',''))
        return charts

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
        'name':fields.char('Name', required=True, size=64,
            help="Name of the fiscal year as displayed on screens."),
        'code':fields.char('Code', required=True, size=64,
            help="Name of the fiscal year as displayed in reports."),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period':fields.selection([('month','Month'), ('3months','3 Months')],
                                  'Periods', required=True),
        'account_name':fields.char('Name', size=128),
        'account_type':fields.selection([('cash','Cash'),('check','Check'),('bank','Bank')], 'Type', size=32),
        'account_currency':fields.many2one('res.currency', 'Currency')
        }
    _defaults = {
        'code': lambda *a: time.strftime('%Y'),
        'name': lambda *a: time.strftime('%Y'),
        'date_start': lambda *a: time.strftime('%Y-01-01'),
        'date_stop': lambda *a: time.strftime('%Y-12-31'),
        'period':lambda *a:'month',
        'account_currency': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
        }

    def on_change_start_date(self, cr, uid, id, start_date):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_date = (start_date + relativedelta(months=12)) - relativedelta(days=1)
            return {'value':{'date_stop':end_date.strftime('%Y-%m-%d')}}
        return {}

    def execute(self, cr, uid, ids, context=None):
        super(account_installer, self).execute(cr, uid, ids, context=context)
        for res in self.read(cr,uid,ids):
            if 'date1' in res and 'date2' in res:
                res_obj = self.pool.get('account.fiscalyear')
                name = res['name']
                vals = {'name':res['name'],
                        'code':res['code'],
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
