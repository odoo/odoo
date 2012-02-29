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

from osv import fields, osv

class account_configuration(osv.osv_memory):
    _inherit = 'res.config'

    _columns = {
            'tax_policy': fields.selection([
                ('no_tax', 'No Tax'),
                ('global_on_order', 'Global On Order'),
                ('on_order_line', 'On Order Lines'),
            ], 'Taxes', required=True),
            'tax_value': fields.float('Value'),
    }
    
    _defaults = {
        'tax_policy': 'global_on_order',
    }
    
    def _check_default_tax(self, cr, uid, context=None):
        ir_values_obj = self.pool.get('ir.values')
        for tax in ir_values_obj.get(cr, uid, 'default', False, ['product.product']):
            if tax[1] == 'taxes_id':
                return tax[2]
        return False
    
    def default_get(self, cr, uid, fields_list, context=None):
        ir_values_obj = self.pool.get('ir.values')
        res = super(account_configuration, self).default_get(cr, uid, fields_list, context=context)
        res.update({'tax_value': 15.0})
        tax_id = self._check_default_tax(cr, uid, context)
        if tax_id:
            res.update({'tax_value': tax_id and tax_id[0]})
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        ir_values_obj = self.pool.get('ir.values')
        res = super(account_configuration, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        if self._check_default_tax(cr, uid, context) and res['fields'].get('tax_value'):
            res['fields']['tax_value'] = {'domain': [], 'views': {}, 'context': {}, 'selectable': True, 'type': 'many2one', 'relation': 'account.tax', 'string': 'Value'}
        return res

    def set_tax_value(self, cr, uid, ids, vals, context=None):
        chart_account_obj = self.pool.get('wizard.multi.charts.accounts')
        acc_installer_obj = self.pool.get('account.installer')
        chart_template_obj = self.pool.get('account.chart.template')
        tax_template_obj = self.pool.get('account.tax.template')
        chart_template_ids = chart_template_obj.search(cr, uid, [('visible', '=', True)], context=context)
        if chart_template_ids:
            taxes = tax_template_obj.search(cr, uid, [('chart_template_id', '=', chart_template_ids[0])], context=context)
        result = {}
        if not self._check_default_tax(cr, uid, context) and not taxes:
            installer_id = acc_installer_obj.create(cr, uid, {}, context=context)
            acc_installer_obj.execute(cr, uid, [installer_id], context=context)
            if chart_template_ids:
                code_digits = chart_account_obj.onchange_chart_template_id(cr, uid, [], chart_template_ids[0], context=context)['value']['code_digits']
                object_id = chart_account_obj.create(cr, uid, {'code_digits': code_digits}, context=context)
                chart_account_obj.execute(cr, uid, [object_id], context=context)
        return result
    
account_configuration()