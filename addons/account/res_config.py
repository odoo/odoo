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
import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from os.path import join as opj

from tools.translate import _
from osv import osv, fields
import tools

class account_config_settings(osv.osv_memory):
    _name = 'account.config.settings'
    _inherit = 'res.config.settings'

    def _get_charts(self, cr, uid, context=None):
        modules = self.pool.get('ir.module.module')
        # Looking for the module with the 'Account Charts' category
        category_name, category_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'module_category_localization_account_charts')
        ids = modules.search(cr, uid, [('category_id', '=', category_id)], context=context)
        charts = list(
            sorted(((m.name, m.shortdesc)
                    for m in modules.browse(cr, uid, ids, context=context)),
                   key=itemgetter(1)))
        charts.insert(0, ('configurable', 'Generic Chart Of Accounts'))
        return charts

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'has_default_company': fields.boolean('Has default company', readonly=True),

        'currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency',
            string='Main currency', help="Main currency of the company."),
        'paypal_account': fields.related('company_id', 'paypal_account', type='char', size=128,
            string='Paypal account', help="Paypal username (usually email) for receiving online payments."),
        'company_footer': fields.related('company_id', 'rml_footer2', type='char', size=250, readonly=True,
            string='Footer of reports', help="Footer of reports based on your bank accounts."),

        'has_account_chart': fields.boolean('Has a chart of accounts'),
        'has_fiscal_year': fields.boolean('Has a fiscal year'),
        'charts': fields.selection(_get_charts, 'Chart of Accounts', required=True,
            help="""Installs localized accounting charts to match as closely as
                possible the accounting needs of your company based on your country."""),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period': fields.selection([('month', 'Monthly'), ('3months','3 Monthly')], 'Periods', required=True),

        'sale_journal_id': fields.many2one('account.journal', 'Sale Journal'),
        'sale_sequence_prefix': fields.related('sale_journal_id', 'sequence_id', 'prefix', type='char', string='Invoice Sequence'),
        'sale_sequence_next': fields.related('sale_journal_id', 'sequence_id', 'number_next', type='integer', string='Invoice Sequence Next Number'),
        'sale_refund_journal_id': fields.many2one('account.journal', 'Sale Refund Journal'),
        'sale_refund_sequence_prefix': fields.related('sale_refund_journal_id', 'sequence_id', 'prefix', type='char', string='Refund Sequence'),
        'sale_refund_sequence_next': fields.related('sale_refund_journal_id', 'sequence_id', 'number_next', type='integer', string='Refund Sequence Next Number'),
        'purchase_journal_id': fields.many2one('account.journal', 'Purchase Journal'),
        'purchase_sequence_prefix': fields.related('purchase_journal_id', 'sequence_id', 'prefix', type='char', string='Supplier Invoice Sequence'),
        'purchase_sequence_next': fields.related('purchase_journal_id', 'sequence_id', 'number_next', type='integer', string='Supplier Invoice Sequence Next Number'),
        'purchase_refund_journal_id': fields.many2one('account.journal', 'Purchase Refund Journal'),
        'purchase_refund_sequence_prefix': fields.related('purchase_refund_journal_id', 'sequence_id', 'prefix', type='char', string='Supplier Refund Sequence'),
        'purchase_refund_sequence_next': fields.related('purchase_refund_journal_id', 'sequence_id', 'number_next', type='integer', string='Supplier Refund Sequence Next Number'),

        'module_account_check_writing': fields.boolean('Support check writings',
            help="""This allows you to check writing and printing.
                This installs the module account_check_writing."""),
        'module_account_accountant': fields.boolean('Accountant Features',
            help="""This allows you to access all the accounting features, like the journal items and the chart of accounts.
                This installs the module account_accountant."""),
        'module_account_asset': fields.boolean('Assets Management',
            help="""This allows you to manage the assets owned by a company or a person.
                It keeps track of the depreciation occurred on those assets, and creates account move for those depreciation lines.
                This installs the module account_asset."""),
        'module_account_budget': fields.boolean('Budgets Management',
            help="""This allows accountants to manage analytic and crossovered budgets.
                Once the master budgets and the budgets are defined,
                the project managers can set the planned amount on each analytic account.
                This installs the module account_budget."""),
        'module_account_payment': fields.boolean('Supplier Payment Orders',
            help="""This allows you to create and manage your payment orders, with purposes to
                    * serve as base for an easy plug-in of various automated payment mechanisms, and
                    * provide a more efficient way to manage invoice payments.
                This installs the module account_payment."""),
        'module_account_voucher': fields.boolean('Manage Customer Payments',
            help="""This includes all the basic requirements of voucher entries for bank, cash, sales, purchase, expense, contra, etc.
                This installs the module account_voucher."""),
        'module_account_followup': fields.boolean('Customer Follow-Ups',
            help="""This allows to automate letters for unpaid invoices, with multi-level recalls.
                This installs the module account_followup."""),
        'module_account_analytic_plans': fields.boolean('Support Multiple Analytic Plans',
            help="""This allows to use several analytic plans, according to the general journal.
                This installs the module account_analytic_plans."""),
        'module_account_analytic_default': fields.boolean('Rules for Analytic Assignation',
            help="""Set default values for your analytic accounts.
                Allows to automatically select analytic accounts based on criteria like product, partner, user, company, date.
                This installs the module account_analytic_default."""),
        'module_account_invoice_layout': fields.boolean('Allow notes and subtotals',
            help="""This provides some features to improve the layout of invoices.
                It gives you the possibility to:
                    * order all the lines of an invoice
                    * add titles, comment lines, sub total lines
                    * draw horizontal lines and put page breaks.
                This installs the module account_invoice_layout."""),

        'group_analytic_account_for_sales': fields.boolean('Analytic Accounting for Sales',
            implied_group='base.group_analytic_account_for_sales',
            help="Allows you to specify an analytic account on sale orders."),
        'group_analytic_account_for_purchase': fields.boolean('Analytic Accounting for Purchases',
            implied_group='base.group_analytic_account_for_purchase',
            help="Allows you to specify an analytic account on purchase orders."),
        'group_dates_periods': fields.boolean('Allow dates/periods',
            implied_group='base.group_dates_periods',
            help="Allows you to keep the period same as your invoice date when you validate the invoice."),
        'group_proforma_invoices': fields.boolean('Allow Pro-forma Invoices',
            implied_group='base.group_proforma_invoices',
            help="Allows you to put invoices in pro-forma state."),

        'complete_tax_set': fields.boolean('Complete Set of Taxes'),
        'sale_tax': fields.many2one('account.tax.template', 'Default Sale Tax', domain="[('type_tax_use','=','sale')]"),
        'purchase_tax': fields.many2one('account.tax.template', 'Default Purchase Tax', domain="[('type_tax_use','=','purchase')]"),
        'sale_tax_rate': fields.float('Sales Tax (%)'),
        'purchase_tax_rate': fields.float('Purchase Tax (%)'),
    }

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.id

    def _default_has_default_company(self, cr, uid, context=None):
        count = self.pool.get('res.company').search_count(cr, uid, [], context=context)
        return bool(count == 1)

    _defaults = {
        'company_id': _default_company,
        'has_default_company': _default_has_default_company,
        'date_start': lambda *a: time.strftime('%Y-01-01'),
        'date_stop': lambda *a: time.strftime('%Y-12-31'),
        'period': 'month',
        'charts': 'configurable',
    }

    def set_default_taxes(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, uid, 'product.template', 'taxes_id', config.sale_tax.id, company_id=config.company_id.id)
        ir_values.set_default(cr, uid, 'product.template', 'supplier_taxes_id', config.purchase_tax.id, company_id=config.company_id.id)

    def on_change_start_date(self, cr, uid, id, start_date=False):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_date = (start_date + relativedelta(months=12)) - relativedelta(days=1)
            return {'value': {'date_stop': end_date.strftime('%Y-%m-%d')}}
        return {}

    def onchange_company_id(self, cr, uid, ids, company_id):
        # update related fields
        company = self.pool.get('res.company').browse(cr, uid, company_id)
        has_account_chart = company_id not in self.pool.get('account.installer').get_unconfigured_cmp(cr, uid)
        has_fiscal_year = self.pool.get('account.fiscalyear').search_count(cr, uid,
            [('date_start', '=', time.strftime('%Y-01-01')), ('date_stop', '=', time.strftime('%Y-12-31')),
             ('company_id', '=', company_id)])
        values = {
            'currency_id': company.currency_id.id,
            'paypal_account': company.paypal_account,
            'company_footer': company.rml_footer2,
            'has_account_chart': has_account_chart,
            'complete_tax_set': has_account_chart,
            'has_fiscal_year': has_fiscal_year,
        }
        # update journals and sequences
        for journal_type in ('sale', 'sale_refund', 'purchase', 'purchase_refund'):
            for suffix in ('_journal_id', '_sequence_prefix', '_sequence_next'):
                values[journal_type + suffix] = False
        journal_obj = self.pool.get('account.journal')
        journal_ids = journal_obj.search(cr, uid, [('company_id', '=', company_id)])
        for journal in journal_obj.browse(cr, uid, journal_ids):
            if journal.type in ('sale', 'sale_refund', 'purchase', 'purchase_refund'):
                values.update({
                    journal.type + '_journal_id': journal.id,
                    journal.type + '_sequence_prefix': journal.sequence_id.prefix,
                    journal.type + '_sequence_next': journal.sequence_id.number_next,
                })
        # update taxes
        ir_values = self.pool.get('ir.values')
        taxes_id = ir_values.get_default(cr, uid, 'product.template', 'taxes_id', company_id=company_id)
        supplier_taxes_id = ir_values.get_default(cr, uid, 'product.template', 'supplier_taxes_id', company_id=company_id)
        values.update({
            'sale_tax': isinstance(taxes_id, list) and taxes_id[0] or taxes_id,
            'purchase_tax': isinstance(supplier_taxes_id, list) and supplier_taxes_id[0] or supplier_taxes_id,
            'sale_tax_rate': 15.0,
            'purchase_tax_rate': 15.0,
        })
        return {'value': values}

    def install_chartofaccounts(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        if config.charts == 'configurable':
            #load generic chart of account
            fp = tools.file_open(opj('account', 'configurable_account_chart.xml'))
            tools.convert_xml_import(cr, 'account', fp, {}, 'init', True, None)
            fp.close()
        elif config.charts.startswith('l10n_'):
            ir_module = self.pool.get('ir.module.module')
            mod_ids = ir_module.search(cr, uid, [('name','=',config.charts)])
            if mod_ids and ir_module.browse(cr, uid, mod_ids[0], context).state == 'uninstalled':
                ir_module.button_immediate_install(cr, uid, mod_ids, context)
        # launch the wizard that creates the account chart from a template
        ir_model_data = self.pool.get('ir.model.data')
        view = ir_model_data.get_object(cr, uid, 'account', 'view_wizard_multi_chart', context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.multi.charts.accounts',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view.id,
            'target': 'new',
            'context': str({'default_company_id': config.company_id.id}),
        }

    def configure_fiscalyear(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        fy_obj = self.pool.get('account.fiscalyear')
        fy_count = fy_obj.search_count(cr, uid,
            [('date_start', '<=', config.date_start), ('date_stop', '>=', config.date_stop),
             ('company_id', '=', config.company_id.id)],
            context=context)
        if not fy_count:
            name = code = config.date_start[:4]
            if int(name) != int(config.date_stop[:4]):
                name = config.date_start[:4] +'-'+ config.date_stop[:4]
                code = config.date_start[2:4] +'-'+ config.date_stop[2:4]
            vals = {
                'name': name,
                'code': code,
                'date_start': config.date_start,
                'date_stop': config.date_stop,
                'company_id': config.company_id.id,
            }
            fiscal_id = fy_obj.create(cr, uid, vals, context=context)
            if config.period == 'month':
                fy_obj.create_period(cr, uid, [fiscal_id])
            elif config.period == '3months':
                fy_obj.create_period3(cr, uid, [fiscal_id])
        # reopen the current wizard to refresh the view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.config.settings',
            'view_type': 'form',
            'view_mode': 'form',
            'context': str({'default_company_id': config.company_id.id}),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
