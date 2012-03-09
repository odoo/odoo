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

from operator import itemgetter

from osv import fields, osv
from tools.translate import _

class account_configuration(osv.osv_memory):
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
            'company_id': fields.many2one('res.company', 'Company'),
            'currency_id': fields.many2one('res.currency','Main Currency'),
            'sale_tax': fields.float('Default Sale Tax'),
            'purchase_tax': fields.float('Default Purchase Tax'),
            'charts': fields.selection(_get_charts, 'Chart of Accounts',
                                        required=True,
                                        help="Installs localized accounting charts to match as closely as "
                                             "possible the accounting needs of your company based on your "
                                             "country."),
            'chart_template_id': fields.many2one('account.chart.template', 'Chart Template'),
            'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year'),
            'paypal_account': fields.char("Your Paypal Account", size=128, help="Paypal username (usually email) for receiving online payments."),
            'company_footer': fields.char("Footer of Reports", size=128),
            'customer_invoice_sequence_prefix': fields.char('Invoice Sequence', size=64),
            'customer_invoice_sequence_padding': fields.integer('Invoice Sequence Padding'),
            'customer_refund_sequence_prefix': fields.char('Refund Sequence', size=64),
            'customer_refund_sequence_padding': fields.integer('Refund Sequence Padding'),
            'supplier_invoice_sequence_prefix': fields.char('Supplier Invoice Sequence', size=64),
            'supplier_invoice_sequence_padding': fields.integer('Supplier Invoice Sequence Padding'),
            'supplier_refund_sequence_prefix': fields.char('Supplier Refund Sequence', size=64),
            'supplier_refund_sequence_padding': fields.integer('Supplier Refund Sequence Padding'),

            'module_account_check_writing': fields.boolean('Support check writings'),
            'module_account_accountant': fields.boolean('Accountant Features'),
            'module_account_asset': fields.boolean('Assets Management'),
            'module_account_budget': fields.boolean('Budgets Management'),
            'module_account_payment': fields.boolean('Supplier Payment Orders'),
            'module_account_voucher': fields.boolean('Manage Customer Payments'),
            'module_account_followup': fields.boolean('Customer Follow-Ups'),
            'module_account_analytic_plans': fields.boolean('Support Multiple Analytic Plans'),
            'module_account_analytic_default': fields.boolean('Rules for Analytic Assignation'),
            'module_account_invoice_layout': fields.boolean('Allow notes and subtotals'),

            'group_analytic_account_for_sales': fields.boolean('Analytic Accounting for Sales', group='base.group_user', implied_group='base.group_analytic_account_for_sales'),
            'group_analytic_account_for_purchase': fields.boolean('Analytic Accounting for Purchase', group='base.group_user', implied_group='base.group_analytic_account_for_purchase'),
            'group_dates_periods': fields.boolean('Allow dates/periods', group='base.group_user', implied_group='base.group_dates_periods'),
            'group_proforma_invoices': fields.boolean('Allow Pro-forma Invoices', group='base.group_user', implied_group='base.group_proforma_invoices'),
    }

    _defaults = {
            'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
            'currency_id': lambda s, cr, uid, c: s.pool.get('res.currency').search(cr, uid, [])[0],
            'charts': 'configurable',
    }

    def _check_default_tax(self, cr, uid, context=None):
        ir_values_obj = self.pool.get('ir.values')
        taxes = {}
        for tax in ir_values_obj.get(cr, uid, 'default', False, ['product.product']):
            if tax[1] == 'taxes_id':
                taxes.update({'taxes_id': tax[2]})
            if tax[1] == 'supplier_taxes_id':
                taxes.update({'supplier_taxes_id': tax[2]})
            return taxes
        return False

    def default_get(self, cr, uid, fields_list, context=None):
        ir_values_obj = self.pool.get('ir.values')
        chart_template_obj = self.pool.get('account.chart.template')
        res = super(account_configuration, self).default_get(cr, uid, fields_list, context=context)
        res.update({'sale_tax': 15.0, 'purchase_tax': 15.0})
        taxes = self._check_default_tax(cr, uid, context)
        chart_template_ids = chart_template_obj.search(cr, uid, [('visible', '=', True)], context=context)
        if chart_template_ids:
            res.update({'chart_template_id': chart_template_ids[0]})
        if taxes:
            sale_tax_id = taxes.get('taxes_id')
            res.update({'sale_tax': sale_tax_id and sale_tax_id[0]})
            purchase_tax_id = taxes.get('supplier_taxes_id')
            res.update({'purchase_tax': purchase_tax_id and purchase_tax_id[0]})
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        ir_values_obj = self.pool.get('ir.values')
        res = super(account_configuration, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        if self._check_default_tax(cr, uid, context) and taxes:
            if res['fields'].get('sale_tax') and res['fields'].get('purchase_tax'):
                res['fields']['sale_tax'] = {'domain': [], 'views': {}, 'context': {}, 'selectable': True, 'type': 'many2one', 'relation': 'account.tax', 'string': 'Default Sale Tax'}
                res['fields']['purchase_tax'] = {'domain': [], 'views': {}, 'context': {}, 'selectable': True, 'type': 'many2one', 'relation': 'account.tax', 'string': 'Default Purchase Tax'}
        return res

account_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: