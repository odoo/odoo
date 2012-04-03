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

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'has_default_company': fields.boolean('Has default company', readonly=True),

        'expects_chart_of_accounts': fields.related('company_id', 'expects_chart_of_accounts', type='boolean',
            string='Chart of Accounts for this Company'),
        'currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency', required=True,
            string='Main currency', help="Main currency of the company."),
        'paypal_account': fields.related('company_id', 'paypal_account', type='char', size=128,
            string='Paypal account', help="Paypal account (email) for receiving online payments (credit card, etc.)"),
        'company_footer': fields.related('company_id', 'rml_footer2', type='char', size=250, readonly=True,
            string='Bank Accounts on Reports', help="Bank accounts as printed on footer of reports."),

        'has_chart_of_accounts': fields.boolean('Company has a chart of accounts'),
        'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', domain="[('visible','=', True)]"),
        'code_digits': fields.integer('# of Digits', help="No. of Digits to use for account code"),
        'seq_journal': fields.boolean('Separated Journal Sequences', help="Check this box if you want to use a different sequence for each created journal. Otherwise, all will use the same sequence."),
        'sale_tax': fields.many2one("account.tax.template", "Default Sale Tax"),
        'purchase_tax': fields.many2one("account.tax.template", "Default Purchase Tax"),
        'sale_tax_rate': fields.float('Sales Tax (%)'),
        'purchase_tax_rate': fields.float('Purchase Tax (%)'),
        'complete_tax_set': fields.boolean('Complete Set of Taxes', help='This boolean helps you to choose if you want to propose to the user to encode the sales and purchase rates or use the usual m2o fields. This last choice assumes that the set of tax defined for the chosen template is complete'),

        'has_fiscal_year': fields.boolean('Company has a fiscal year'),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period': fields.selection([('month', 'Monthly'), ('3months','3 Monthly')], 'Periods', required=True),

        'sale_journal_id': fields.many2one('account.journal', 'Sale Journal'),
        'sale_sequence_prefix': fields.related('sale_journal_id', 'sequence_id', 'prefix', type='char', string='Invoice Sequence'),
        'sale_sequence_next': fields.related('sale_journal_id', 'sequence_id', 'number_next', type='integer', string='Next Invoice Number'),
        'sale_refund_journal_id': fields.many2one('account.journal', 'Sale Refund Journal'),
        'sale_refund_sequence_prefix': fields.related('sale_refund_journal_id', 'sequence_id', 'prefix', type='char', string='Refund Sequence'),
        'sale_refund_sequence_next': fields.related('sale_refund_journal_id', 'sequence_id', 'number_next', type='integer', string='Next Refund Number'),
        'purchase_journal_id': fields.many2one('account.journal', 'Purchase Journal'),
        'purchase_sequence_prefix': fields.related('purchase_journal_id', 'sequence_id', 'prefix', type='char', string='Supplier Invoice Sequence'),
        'purchase_sequence_next': fields.related('purchase_journal_id', 'sequence_id', 'number_next', type='integer', string='Next Supplier Invoice Number'),
        'purchase_refund_journal_id': fields.many2one('account.journal', 'Purchase Refund Journal'),
        'purchase_refund_sequence_prefix': fields.related('purchase_refund_journal_id', 'sequence_id', 'prefix', type='char', string='Supplier Refund Sequence'),
        'purchase_refund_sequence_next': fields.related('purchase_refund_journal_id', 'sequence_id', 'number_next', type='integer', string='Next Supplier Refund Number'),

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

        'group_proforma_invoices': fields.boolean('Allow Pro-forma Invoices',
            implied_group='account.group_proforma_invoices',
            help="Allows you to put invoices in pro-forma state."),

        'default_sale_tax': fields.many2one('account.tax', 'Default Sale Tax'),
        'default_purchase_tax': fields.many2one('account.tax', 'Default Purchase Tax'),
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
        'seq_journal': True,
        'date_start': lambda *a: time.strftime('%Y-01-01'),
        'date_stop': lambda *a: time.strftime('%Y-12-31'),
        'period': 'month',
    }

    def create(self, cr, uid, values, context=None):
        id = super(account_config_settings, self).create(cr, uid, values, context)
        # Hack: to avoid some nasty bug, related fields are not written upon record creation.
        # Hence we write on those fields here.
        vals = {}
        for fname, field in self._columns.iteritems():
            if isinstance(field, fields.related) and fname in values:
                vals[fname] = values[fname]
        self.write(cr, uid, [id], vals, context)
        return id

    def onchange_company_id(self, cr, uid, ids, company_id):
        # update related fields
        company = self.pool.get('res.company').browse(cr, uid, company_id)
        has_chart_of_accounts = company_id not in self.pool.get('account.installer').get_unconfigured_cmp(cr, uid)
        fiscalyear_count = self.pool.get('account.fiscalyear').search_count(cr, uid,
            [('date_start', '<=', time.strftime('%Y-%m-%d')), ('date_stop', '>=', time.strftime('%Y-%m-%d')),
             ('company_id', '=', company_id)])
        values = {
            'expects_chart_of_accounts': company.expects_chart_of_accounts,
            'currency_id': company.currency_id.id,
            'paypal_account': company.paypal_account,
            'company_footer': company.rml_footer2,
            'has_chart_of_accounts': has_chart_of_accounts,
            'has_fiscal_year': bool(fiscalyear_count),
            'chart_template_id': False,
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
        taxes_id = ir_values.get_default(cr, uid, 'product.product', 'taxes_id', company_id=company_id)
        supplier_taxes_id = ir_values.get_default(cr, uid, 'product.product', 'supplier_taxes_id', company_id=company_id)
        values.update({
            'default_sale_tax': isinstance(taxes_id, list) and taxes_id[0] or taxes_id,
            'default_purchase_tax': isinstance(supplier_taxes_id, list) and supplier_taxes_id[0] or supplier_taxes_id,
        })
        return {'value': values}

    def onchange_chart_template_id(self, cr, uid, ids, chart_template_id, context=None):
        tax_templ_obj = self.pool.get('account.tax.template')
        res = {'value': {
            'complete_tax_set': False, 'sale_tax': False, 'purchase_tax': False,
            'sale_tax_rate': 15, 'purchase_tax_rate': 15,
        }}
        if chart_template_id:
            # update complete_tax_set, sale_tax and purchase_tax
            chart_template = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
            res['value'].update({'complete_tax_set': chart_template.complete_tax_set})
            if chart_template.complete_tax_set:
                # default tax is given by the lowest sequence. For same sequence we will take the latest created as it will be the case for tax created while isntalling the generic chart of account
                sale_tax_ids = tax_templ_obj.search(cr, uid,
                    [("chart_template_id", "=", chart_template_id), ('type_tax_use', 'in', ('sale','all'))],
                    order="sequence, id desc")
                purchase_tax_ids = tax_templ_obj.search(cr, uid,
                    [("chart_template_id", "=", chart_template_id), ('type_tax_use', 'in', ('purchase','all'))],
                    order="sequence, id desc")
                res['value']['sale_tax'] = sale_tax_ids and sale_tax_ids[0] or False
                res['value']['purchase_tax'] = purchase_tax_ids and purchase_tax_ids[0] or False
            if chart_template.code_digits:
                res['value']['code_digits'] = chart_template.code_digits
        return res

    def onchange_tax_rate(self, cr, uid, ids, rate, context=None):
        return {'value': {'purchase_tax_rate': rate or False}}

    def onchange_start_date(self, cr, uid, id, start_date):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_date = (start_date + relativedelta(months=12)) - relativedelta(days=1)
            return {'value': {'date_stop': end_date.strftime('%Y-%m-%d')}}
        return {}

    def set_default_taxes(self, cr, uid, ids, context=None):
        """ set default sale and purchase taxes for products """
        ir_values = self.pool.get('ir.values')
        config = self.browse(cr, uid, ids[0], context)
        ir_values.set_default(cr, uid, 'product.product', 'taxes_id',
            config.default_sale_tax and [config.default_sale_tax.id] or False, company_id=config.company_id.id)
        ir_values.set_default(cr, uid, 'product.product', 'supplier_taxes_id',
            config.default_purchase_tax and [config.default_purchase_tax.id] or False, company_id=config.company_id.id)

    def set_chart_of_accounts(self, cr, uid, ids, context=None):
        """ install a chart of accounts for the given company (if required) """
        config = self.browse(cr, uid, ids[0], context)
        if config.chart_template_id:
            assert config.expects_chart_of_accounts and not config.has_chart_of_accounts
            wizard = self.pool.get('wizard.multi.charts.accounts')
            wizard_id = wizard.create(cr, uid, {
                'company_id': config.company_id.id,
                'chart_template_id': config.chart_template_id.id,
                'code_digits': config.code_digits or 6,
                'seq_journal': config.seq_journal,
                'sale_tax': config.sale_tax.id,
                'purchase_tax': config.purchase_tax.id,
                'sale_tax_rate': config.sale_tax_rate,
                'purchase_tax_rate': config.purchase_tax_rate,
                'complete_tax_set': config.complete_tax_set,
            }, context)
            wizard.execute(cr, uid, [wizard_id], context)

    def set_fiscalyear(self, cr, uid, ids, context=None):
        """ create a fiscal year for the given company (if necessary) """
        config = self.browse(cr, uid, ids[0], context)
        if config.has_chart_of_accounts or config.chart_template_id:
            fiscalyear = self.pool.get('account.fiscalyear')
            fiscalyear_count = fiscalyear.search_count(cr, uid,
                [('date_start', '<=', config.date_start), ('date_stop', '>=', config.date_stop),
                 ('company_id', '=', config.company_id.id)],
                context=context)
            if not fiscalyear_count:
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
                fiscalyear_id = fiscalyear.create(cr, uid, vals, context=context)
                if config.period == 'month':
                    fiscalyear.create_period(cr, uid, [fiscalyear_id])
                elif config.period == '3months':
                    fiscalyear.create_period3(cr, uid, [fiscalyear_id])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
