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

import logging
import time
import datetime
from dateutil.relativedelta import relativedelta
from os.path import join as opj
from operator import itemgetter

from tools.translate import _
from osv import fields, osv
import netsvc
import tools

class account_installer(osv.osv_memory):
    _name = 'account.installer'
    _inherit = 'res.config.installer'
    __logger = logging.getLogger(_name)

    def _get_charts(self, cr, uid, context=None):
        modules = self.pool.get('ir.module.module')
        ids = modules.search(cr, uid, [('name', 'like', 'l10n_')], context=context)
        charts = list(
            sorted(((m.name, m.shortdesc)
                    for m in modules.browse(cr, uid, ids, context=context)),
                   key=itemgetter(1)))
        charts.insert(0, ('configurable', 'Generic Chart Of Account'))
        return charts

    _columns = {
        # Accounting
        'charts': fields.selection(_get_charts, 'Chart of Accounts',
            required=True,
            help="Installs localized accounting charts to match as closely as "
                 "possible the accounting needs of your company based on your "
                 "country."),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period': fields.selection([('month', 'Monthly'), ('3months','3 Monthly')], 'Periods', required=True),
        'sale_tax': fields.float('Sale Tax(%)'),
        'purchase_tax': fields.float('Purchase Tax(%)'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id and user.company_id.id or False

    _defaults = {
        'date_start': lambda *a: time.strftime('%Y-01-01'),
        'date_stop': lambda *a: time.strftime('%Y-12-31'),
        'period': 'month',
        'sale_tax': 0.0,
        'purchase_tax': 0.0,
        'company_id': _default_company,
        'charts': 'configurable'
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(account_installer, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        cmp_select = []
        company_ids = self.pool.get('res.company').search(cr, uid, [], context=context)
        #display in the widget selection of companies, only the companies that haven't been configured yet (but don't care about the demo chart of accounts)
        cr.execute("SELECT company_id FROM account_account WHERE active = 't' AND account_account.parent_id IS NULL AND name != %s", ("Chart For Automated Tests",))
        configured_cmp = [r[0] for r in cr.fetchall()]
        unconfigured_cmp = list(set(company_ids)-set(configured_cmp))
        for field in res['fields']:
            if field == 'company_id':
                res['fields'][field]['domain'] = [('id','in',unconfigured_cmp)]
                res['fields'][field]['selection'] = [('', '')]
                if unconfigured_cmp:
                    cmp_select = [(line.id, line.name) for line in self.pool.get('res.company').browse(cr, uid, unconfigured_cmp)]
                    res['fields'][field]['selection'] = cmp_select
        return res

    def on_change_tax(self, cr, uid, id, tax):
        return {'value': {'purchase_tax': tax}}

    def on_change_start_date(self, cr, uid, id, start_date=False):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_date = (start_date + relativedelta(months=12)) - relativedelta(days=1)
            return {'value': {'date_stop': end_date.strftime('%Y-%m-%d')}}
        return {}

    def execute(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        fy_obj = self.pool.get('account.fiscalyear')
        mod_obj = self.pool.get('ir.model.data')
        obj_acc_temp = self.pool.get('account.account.template')
        obj_tax_code_temp = self.pool.get('account.tax.code.template')
        obj_tax_temp = self.pool.get('account.tax.template')
        obj_acc_chart_temp = self.pool.get('account.chart.template')
        record = self.browse(cr, uid, ids, context=context)[0]
        for res in self.read(cr, uid, ids, context=context):
            if record.charts == 'configurable':
                fp = tools.file_open(opj('account', 'configurable_account_chart.xml'))
                tools.convert_xml_import(cr, 'account', fp, {}, 'init', True, None)
                fp.close()
                s_tax = (res.get('sale_tax', 0.0))/100
                p_tax = (res.get('purchase_tax', 0.0))/100
                pur_temp_tax = mod_obj.get_object_reference(cr, uid, 'account', 'tax_code_base_purchases')
                pur_temp_tax_id = pur_temp_tax and pur_temp_tax[1] or False

                pur_temp_tax_paid = mod_obj.get_object_reference(cr, uid, 'account', 'tax_code_output')
                pur_temp_tax_paid_id = pur_temp_tax_paid and pur_temp_tax_paid[1] or False

                sale_temp_tax = mod_obj.get_object_reference(cr, uid, 'account', 'tax_code_base_sales')
                sale_temp_tax_id = sale_temp_tax and sale_temp_tax[1] or False

                sale_temp_tax_paid = mod_obj.get_object_reference(cr, uid, 'account', 'tax_code_input')
                sale_temp_tax_paid_id = sale_temp_tax_paid and sale_temp_tax_paid[1] or False

                chart_temp_ids = obj_acc_chart_temp.search(cr, uid, [('name','=','Configurable Account Chart Template')], context=context)
                chart_temp_id = chart_temp_ids and chart_temp_ids[0] or False
                if s_tax * 100 > 0.0:
                    tax_account_ids = obj_acc_temp.search(cr, uid, [('name', '=', 'Tax Received')], context=context)
                    sales_tax_account_id = tax_account_ids and tax_account_ids[0] or False
                    vals_tax_code_temp = {
                        'name': _('TAX %s%%') % (s_tax*100),
                        'code': _('TAX %s%%') % (s_tax*100),
                        'parent_id': sale_temp_tax_id
                    }
                    new_tax_code_temp = obj_tax_code_temp.create(cr, uid, vals_tax_code_temp, context=context)
                    vals_paid_tax_code_temp = {
                        'name': _('TAX Received %s%%') % (s_tax*100),
                        'code': _('TAX Received %s%%') % (s_tax*100),
                        'parent_id': sale_temp_tax_paid_id
                    }
                    new_paid_tax_code_temp = obj_tax_code_temp.create(cr, uid, vals_paid_tax_code_temp, context=context)
                    sales_tax_temp = obj_tax_temp.create(cr, uid, {
                                            'name': _('Sale TAX %s%%') % (s_tax*100),
                                            'amount': s_tax,
                                            'base_code_id': new_tax_code_temp,
                                            'tax_code_id': new_paid_tax_code_temp,
                                            'ref_base_code_id': new_tax_code_temp,
                                            'ref_tax_code_id': new_paid_tax_code_temp,
                                            'type_tax_use': 'sale',
                                            'type': 'percent',
                                            'sequence': 0,
                                            'account_collected_id': sales_tax_account_id,
                                            'account_paid_id': sales_tax_account_id,
                                            'chart_template_id': chart_temp_id,
                                }, context=context)
                if p_tax * 100 > 0.0:
                    tax_account_ids = obj_acc_temp.search(cr, uid, [('name', '=', 'Tax Paid')], context=context)
                    purchase_tax_account_id = tax_account_ids and tax_account_ids[0] or False
                    vals_tax_code_temp = {
                        'name': _('TAX %s%%') % (p_tax*100),
                        'code': _('TAX %s%%') % (p_tax*100),
                        'parent_id': pur_temp_tax_id
                    }
                    new_tax_code_temp = obj_tax_code_temp.create(cr, uid, vals_tax_code_temp, context=context)
                    vals_paid_tax_code_temp = {
                        'name': _('TAX Paid %s%%') % (p_tax*100),
                        'code': _('TAX Paid %s%%') % (p_tax*100),
                        'parent_id': pur_temp_tax_paid_id
                    }
                    new_paid_tax_code_temp = obj_tax_code_temp.create(cr, uid, vals_paid_tax_code_temp, context=context)
                    purchase_tax_temp = obj_tax_temp.create(cr, uid, {
                                             'name': _('Purchase TAX %s%%') % (p_tax*100),
                                             'description': _('TAX %s%%') % (p_tax*100),
                                             'amount': p_tax,
                                             'base_code_id': new_tax_code_temp,
                                             'tax_code_id': new_paid_tax_code_temp,
                                             'ref_base_code_id': new_tax_code_temp,
                                             'ref_tax_code_id': new_paid_tax_code_temp,
                                             'type_tax_use': 'purchase',
                                             'type': 'percent',
                                             'sequence': 0,
                                             'account_collected_id': purchase_tax_account_id,
                                             'account_paid_id': purchase_tax_account_id,
                                             'chart_template_id': chart_temp_id,
                                    }, context=context)

            if 'date_start' in res and 'date_stop' in res:
                f_ids = fy_obj.search(cr, uid, [('date_start', '<=', res['date_start']), ('date_stop', '>=', res['date_stop']), ('company_id', '=', res['company_id'][0])], context=context)
                if not f_ids:
                    name = code = res['date_start'][:4]
                    if int(name) != int(res['date_stop'][:4]):
                        name = res['date_start'][:4] +'-'+ res['date_stop'][:4]
                        code = res['date_start'][2:4] +'-'+ res['date_stop'][2:4]
                    vals = {
                        'name': name,
                        'code': code,
                        'date_start': res['date_start'],
                        'date_stop': res['date_stop'],
                        'company_id': res['company_id'][0]
                    }
                    fiscal_id = fy_obj.create(cr, uid, vals, context=context)
                    if res['period'] == 'month':
                        fy_obj.create_period(cr, uid, [fiscal_id])
                    elif res['period'] == '3months':
                        fy_obj.create_period3(cr, uid, [fiscal_id])
        super(account_installer, self).execute(cr, uid, ids, context=context)

    def modules_to_install(self, cr, uid, ids, context=None):
        modules = super(account_installer, self).modules_to_install(
            cr, uid, ids, context=context)
        chart = self.read(cr, uid, ids, ['charts'],
                          context=context)[0]['charts']
        self.__logger.debug('Installing chart of accounts %s', chart)
        return modules | set([chart])

account_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
